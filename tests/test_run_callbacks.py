"""Exercise real Dash callbacks with isolated runner doubles, never production data."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.run_logging import execution_id
from src.ui import ids
from src.ui.callbacks import (
    flushing_callbacks,
    hydraulic_callbacks,
    partitioning_callbacks,
)


class CallbackRegistry:
    def __init__(self):
        self.functions = {}

    def callback(self, *args, **kwargs):
        def register(function):
            self.functions[function.__name__] = function
            return function

        return register


class RunCallbackTests(unittest.TestCase):
    def test_real_callbacks_preserve_results_parameters_and_handled_errors(self):
        registry = CallbackRegistry()
        hydraulic_callbacks.register_hydraulic_callbacks(registry)
        partitioning_callbacks.register_partitioning_callbacks(registry)
        model = {"model_id": "abcdef123456", "filename": "network.inp"}
        state = {
            "run_id": "123456abcdef",
            "model_id": model["model_id"],
            "backend": "wntr",
            "summary": {},
        }
        with (
            patch.object(
                hydraulic_callbacks,
                "resolve_uploaded_model",
                return_value=Path("/test/network.inp"),
            ),
            patch.object(
                hydraulic_callbacks, "call_hydraulic_simulator", return_value=state
            ) as runner,
            patch.object(
                hydraulic_callbacks,
                "render_success_alert",
                return_value="original-success",
            ),
        ):
            result = hydraulic_callbacks._execute_hydraulic_simulation(
                1, model, "wntr", True, 2, 5, 30, 5, 1.2
            )
            self.assertEqual(result, (state, "original-success"))
            self.assertEqual(
                runner.call_args.kwargs["option_overrides"],
                {
                    "duration": 7200,
                    "hydraulic_timestep": 300,
                    "report_timestep": 1800,
                    "rule_timestep": 300,
                    "demand_multiplier": 1.2,
                },
            )
            with self.assertLogs("src.run_logging", level="INFO") as logs:
                failed = hydraulic_callbacks._execute_hydraulic_simulation(
                    1, model, "wntr", True, None, 5, 30, 5, 1.0
                )
            self.assertIsNone(failed[0])
            self.assertTrue(any('"status":"failed"' in line for line in logs.output))
        with (
            patch.object(
                partitioning_callbacks,
                "resolve_uploaded_model",
                return_value=Path("/test/network.inp"),
            ),
            patch.object(
                partitioning_callbacks, "call_staci_split_service", return_value=state
            ) as runner,
            patch.object(
                partitioning_callbacks,
                "render_success_alert",
                return_value="original-success",
            ),
        ):
            result = partitioning_callbacks._execute_partitioning(
                1, model, 3, "modularity", "topology", "diameter", 20, 50, 0.25, 0.8, 42
            )
            self.assertEqual(result, (state, "original-success"))
            self.assertEqual(runner.call_args.kwargs["seed"], 42)
            self.assertEqual(
                runner.call_args.kwargs["optimizer_settings"]["popsize"], 20
            )
        self.assertEqual(execution_id.get(), "-")

    def test_dash_http_background_callback_accepts_reserved_job(self):
        from app import app
        from src.background_jobs import background_callback_manager

        key, callback = next(
            (key, value)
            for key, value in app.callback_map.items()
            if "hyd-run-store.data" in key and "hyd-run-status.children" in key
        )
        request_state = {
            "token": "fixture-token",
            "workflow": "hydraulic",
            "payload": {
                "network_state": None,
                "backend": "wntr",
                "override_enabled": False,
                "duration": 1,
                "hydraulic_timestep": 5,
                "report_timestep": 60,
                "rule_timestep": 5,
                "demand_multiplier": 1.0,
            },
        }

        body = {
            "output": key,
            "outputs": [
                {
                    "id": item.component_id,
                    "property": item.component_property,
                }
                for item in callback["output"]
            ],
            "inputs": [
                dict(
                    callback["inputs"][0],
                    value=request_state,
                )
            ],
            "state": [],
            "changedPropIds": [f"{ids.HYD_JOB_REQUEST_STORE}.data"],
        }
        with (
            patch.object(
                background_callback_manager, "call_job_fn", return_value="fixture-job"
            ) as submit,
            patch.object(
                app, "_get_signing_secret", return_value=b"fixture-secret" * 4
            ),
        ):
            response = app.server.test_client().post(
                "/staci-app/_dash-update-component",
                json=body,
                headers={"X-Staci-User-Id": "7", "X-Staci-User-Login": "worker-test"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("job", response.get_json())
        self.assertEqual(
            submit.call_args.args[2],
            [request_state],
        )
        self.assertEqual(submit.call_args.args[3]["headers"]["X-Staci-User-Id"], "7")

    def test_hydraulic_runner_records_effective_copied_input_before_solver(self):
        from src.services import hydraulic_runner

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.inp"
            original.write_text("original")

            def override(source, options, destination):
                destination.write_text("effective")

            with (
                patch.object(hydraulic_runner, "RUN_ROOT", root / "runs"),
                patch.object(
                    hydraulic_runner, "set_model_options", side_effect=override
                ),
                patch.object(
                    hydraulic_runner,
                    "read_hydraulic_workload_inputs",
                    return_value={
                        "node_count": 10,
                        "link_count": 15,
                        "duration_seconds": 3600,
                        "hydraulic_timestep_seconds": 300,
                        "report_timestep_seconds": 1800,
                    },
                ),
                patch.object(
                    hydraulic_runner,
                    "read_model_options",
                    return_value={"duration": 7200},
                ),
                patch.object(
                    hydraulic_runner, "run_wntr", return_value={"same": "result"}
                ) as solver,
            ):
                token = execution_id.set("f" * 32)
                try:
                    with self.assertLogs("src.run_logging", level="INFO") as logs:
                        result = hydraulic_runner.call_hydraulic_simulator(
                            original,
                            model_id="abcdef123456",
                            backend="wntr",
                            option_overrides={"duration": 7200},
                        )
                finally:
                    execution_id.reset(token)
            self.assertEqual(result, {"same": "result"})
            self.assertEqual(Path(solver.call_args.args[0]).read_text(), "effective")
            self.assertEqual(original.read_text(), "original")
            events = [
                json.loads(line.split("STACI_RUN ", 1)[1])
                for line in logs.output
                if "STACI_RUN " in line
            ]
            prepared = next(e for e in events if e["event"] == "prepared")
            self.assertEqual(prepared["effective_options"]["duration"], 7200)
            self.assertEqual(prepared["run_id"], solver.call_args.args[2])

    def test_hydraulic_submission_reserves_job_before_background_execution(self):
        registry = CallbackRegistry()
        hydraulic_callbacks.register_hydraulic_callbacks(registry)

        model = {
            "model_id": "abcdef123456",
            "filename": "network.inp",
        }
        request_state = {
            "token": "fixture-token",
            "workflow": "hydraulic",
            "payload": {},
        }

        with patch.object(
            hydraulic_callbacks,
            "reserve_solver_job",
            return_value=request_state,
        ) as reserve:
            result = registry.functions["submit_hydraulic_simulation"](
                1,
                model,
                "wntr",
                True,
                2,
                5,
                30,
                5,
                1.2,
            )

        self.assertEqual(
            result[0],
            request_state,
        )
        self.assertEqual(
            reserve.call_args.kwargs["workflow"],
            "hydraulic",
        )
        self.assertEqual(
            reserve.call_args.kwargs["payload"],
            {
                "network_state": model,
                "backend": "wntr",
                "override_enabled": True,
                "duration": 2,
                "hydraulic_timestep": 5,
                "report_timestep": 30,
                "rule_timestep": 5,
                "demand_multiplier": 1.2,
            },
        )

    def test_partition_submission_reserves_job_before_background_execution(self):
        registry = CallbackRegistry()
        partitioning_callbacks.register_partitioning_callbacks(registry)

        model = {
            "model_id": "abcdef123456",
            "filename": "network.inp",
        }
        request_state = {
            "token": "fixture-token",
            "workflow": "partition",
            "payload": {},
        }

        with patch.object(
            partitioning_callbacks,
            "reserve_solver_job",
            return_value=request_state,
        ) as reserve:
            result = registry.functions["submit_partitioning"](
                1,
                model,
                3,
                "modularity",
                "topology",
                "diameter",
                20,
                50,
                0.25,
                0.8,
                42,
            )

        self.assertEqual(
            result[0],
            request_state,
        )
        self.assertEqual(
            reserve.call_args.kwargs["workflow"],
            "partition",
        )
        self.assertEqual(
            reserve.call_args.kwargs["payload"],
            {
                "network_state": model,
                "n_comm": 3,
                "obj_type": "modularity",
                "weight_type": "topology",
                "weight_type_mod": "diameter",
                "popsize": 20,
                "ngen": 50,
                "pmut": 0.25,
                "pcross": 0.8,
                "seed": 42,
            },
        )

    def test_flushing_submission_reserves_job_before_background_execution(self):
        registry = CallbackRegistry()
        flushing_callbacks.register_flushing_callbacks(registry)

        model = {
            "model_id": "abcdef123456",
            "filename": "network.inp",
        }
        request_state = {
            "token": "fixture-token",
            "workflow": "flushing",
            "payload": {},
        }

        with patch.object(
            flushing_callbacks,
            "reserve_solver_job",
            return_value=request_state,
        ) as reserve:
            result = registry.functions["submit_flushing"](
                1,
                model,
                "J1, J2",
                "single",
                0.002,
                2.0,
                0.5,
                0.0,
                False,
            )

        self.assertEqual(
            result[0],
            request_state,
        )
        self.assertEqual(
            reserve.call_args.kwargs["workflow"],
            "flushing",
        )
        self.assertEqual(
            reserve.call_args.kwargs["payload"],
            {
                "network_state": model,
                "hydrant_text": "J1, J2",
                "mode": "single",
                "hydrant_area": 0.002,
                "loss_coefficient": 2.0,
                "velocity_threshold": 0.5,
                "min_pressure_head": 0.0,
                "write_networks": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
