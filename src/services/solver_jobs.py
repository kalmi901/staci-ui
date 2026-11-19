from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal, cast

SolverWorkflow = Literal[
    "hydraulic",
    "partition",
    "flushing",
    "calibration",
]

SolverJobState = Literal[
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
]

TerminalJobState = Literal[
    "completed",
    "failed",
    "cancelled",
]


@dataclass(frozen=True)
class SolverJob:
    token: str
    user_id: str
    workflow: SolverWorkflow
    state: SolverJobState
    submitted_at: float
    started_at: float | None = None
    celery_task_id: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(
        cls,
        value: str,
    ) -> SolverJob:
        data = json.loads(value)

        return cls(
            token=str(data["token"]),
            user_id=str(data["user_id"]),
            workflow=cast(
                SolverWorkflow,
                data["workflow"],
            ),
            state=cast(
                SolverJobState,
                data["state"],
            ),
            submitted_at=float(data["submitted_at"]),
            started_at=(
                float(data["started_at"])
                if data.get("started_at") is not None
                else None
            ),
            celery_task_id=(
                str(data["celery_task_id"])
                if data.get("celery_task_id") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class SolverQueueStatus:
    capacity: int
    running_jobs: int
    queued_jobs: int
    user_job: SolverJob | None
    queue_position: int | None


class ActiveSolverJobError(RuntimeError):
    def __init__(
        self,
        job: SolverJob | None,
    ) -> None:
        self.job = job

        if job is None:
            message = "This user already has an active solver job."
        else:
            message = f"This user already has a {job.state} {job.workflow} job."

        super().__init__(message)


class SolverJobRegistry:
    def __init__(
        self,
        redis_client: Any,
        *,
        ttl_seconds: int,
        capacity: int,
        clock: Callable[[], float] = time.time,
        token_factory: Callable[
            [],
            str,
        ] = lambda: uuid.uuid4().hex,
        key_prefix: str = "staci-ui:solver",
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Solver job TTL must be positive.")

        if capacity <= 0:
            raise ValueError("Solver capacity must be positive.")

        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._clock = clock
        self._token_factory = token_factory
        self._key_prefix = key_prefix

    @property
    def capacity(self) -> int:
        return self._capacity

    def _job_key(
        self,
        token: str,
    ) -> str:
        return f"{self._key_prefix}:job:{token}"

    def _user_key(
        self,
        user_id: str,
    ) -> str:
        return f"{self._key_prefix}:user:{user_id}:active"

    @property
    def _queued_key(self) -> str:
        return f"{self._key_prefix}:queued"

    @property
    def _running_key(self) -> str:
        return f"{self._key_prefix}:running"

    def _clean_expired_members(self) -> None:
        cutoff = self._clock() - self._ttl_seconds

        pipeline = self._redis.pipeline(transaction=True)
        pipeline.zremrangebyscore(
            self._queued_key,
            "-inf",
            cutoff,
        )
        pipeline.zremrangebyscore(
            self._running_key,
            "-inf",
            cutoff,
        )
        pipeline.execute()

    def _release_user_lock(
        self,
        user_id: str,
        token: str,
    ) -> bool:
        key = self._user_key(user_id)

        while True:
            pipeline = self._redis.pipeline()

            try:
                pipeline.watch(key)

                if pipeline.get(key) != token:
                    pipeline.unwatch()
                    return False

                pipeline.multi()
                pipeline.delete(key)
                pipeline.execute()

                return True
            except Exception as exc:
                if exc.__class__.__name__ != "WatchError":
                    raise

    def submit(
        self,
        *,
        user_id: str,
        workflow: SolverWorkflow,
    ) -> SolverJob:
        token = self._token_factory()
        submitted_at = self._clock()

        acquired = self._redis.set(
            self._user_key(user_id),
            token,
            nx=True,
            ex=self._ttl_seconds,
        )

        if not acquired:
            raise ActiveSolverJobError(self.get_user_job(user_id))

        job = SolverJob(
            token=token,
            user_id=user_id,
            workflow=workflow,
            state="queued",
            submitted_at=submitted_at,
        )

        try:
            pipeline = self._redis.pipeline(transaction=True)
            pipeline.set(
                self._job_key(token),
                job.to_json(),
                ex=self._ttl_seconds,
            )
            pipeline.zadd(
                self._queued_key,
                {token: submitted_at},
            )
            pipeline.execute()
        except Exception:
            self._release_user_lock(
                user_id,
                token,
            )
            raise

        return job

    def get_job(
        self,
        token: str,
    ) -> SolverJob | None:
        value = self._redis.get(self._job_key(token))

        if value is None:
            return None

        return SolverJob.from_json(value)

    def get_user_job(
        self,
        user_id: str,
    ) -> SolverJob | None:
        token = self._redis.get(self._user_key(user_id))

        if token is None:
            return None

        job = self.get_job(token)

        if job is None or job.user_id != user_id:
            self._release_user_lock(
                user_id,
                token,
            )
            return None

        return job

    def mark_running(
        self,
        *,
        token: str,
        user_id: str,
        celery_task_id: str | None,
    ) -> SolverJob:
        job = self.get_job(token)

        if job is None:
            raise RuntimeError("Solver job is no longer available.")

        if job.user_id != user_id:
            raise PermissionError("Solver job belongs to another user.")

        if job.state != "queued":
            raise RuntimeError("Solver job is not queued.")

        if self._redis.get(self._user_key(user_id)) != token:
            raise RuntimeError("Solver job reservation expired.")

        started_at = self._clock()

        running_job = replace(
            job,
            state="running",
            started_at=started_at,
            celery_task_id=celery_task_id,
        )

        pipeline = self._redis.pipeline(transaction=True)
        pipeline.zrem(
            self._queued_key,
            token,
        )
        pipeline.zadd(
            self._running_key,
            {token: started_at},
        )
        pipeline.set(
            self._job_key(token),
            running_job.to_json(),
            ex=self._ttl_seconds,
        )
        pipeline.expire(
            self._user_key(user_id),
            self._ttl_seconds,
        )
        pipeline.execute()

        return running_job

    def finish(
        self,
        *,
        token: str,
        user_id: str,
        state: TerminalJobState,
    ) -> SolverJob | None:
        job = self.get_job(token)

        if job is None:
            self._release_user_lock(
                user_id,
                token,
            )
            return None

        if job.user_id != user_id:
            raise PermissionError("Solver job belongs to another user.")

        finished_job = replace(
            job,
            state=state,
        )

        pipeline = self._redis.pipeline(transaction=True)
        pipeline.zrem(
            self._queued_key,
            token,
        )
        pipeline.zrem(
            self._running_key,
            token,
        )
        pipeline.set(
            self._job_key(token),
            finished_job.to_json(),
            ex=self._ttl_seconds,
        )
        pipeline.execute()

        self._release_user_lock(user_id, token)

        return finished_job

    def status_for_user(
        self,
        user_id: str,
    ) -> SolverQueueStatus:
        self._clean_expired_members()

        user_job = self.get_user_job(user_id)

        queue_position = None

        if user_job is not None and user_job.state == "queued":
            rank = self._redis.zrank(
                self._queued_key,
                user_job.token,
            )

            if rank is not None:
                queue_position = int(rank) + 1

        return SolverQueueStatus(
            capacity=self._capacity,
            running_jobs=int(self._redis.zcard(self._running_key)),
            queued_jobs=int(self._redis.zcard(self._queued_key)),
            user_job=user_job,
            queue_position=queue_position,
        )
