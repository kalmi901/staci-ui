from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

MAX_OPTIMIZER_POPULATION = 200
MAX_OPTIMIZER_GENERATIONS = 500
MAX_PARTITION_COMMUNITIES = 100
MAX_RANDOM_SEED = (2**32) - 1


def require_bounded_integer(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    message = f"{label} must be an integer between {minimum:,} and {maximum:,}."

    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(message)

    number = float(value)

    if (
        not math.isfinite(number)
        or not number.is_integer()
        or number < minimum
        or number > maximum
    ):
        raise ValueError(message)

    return int(number)


def require_probability(
    value: Any,
    *,
    label: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(f"{label} must be between 0 and 1.")

    number = float(value)

    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError(f"{label} must be between 0 and 1.")

    return number


def validate_optimizer_settings(
    settings: Mapping[str, Any],
    *,
    minimum_population: int,
) -> dict[str, Any]:
    validated = dict(settings)

    validated["popsize"] = require_bounded_integer(
        validated.get("popsize"),
        label="Population size",
        minimum=minimum_population,
        maximum=MAX_OPTIMIZER_POPULATION,
    )

    validated["ngen"] = require_bounded_integer(
        validated.get("ngen"),
        label="Generation count",
        minimum=1,
        maximum=MAX_OPTIMIZER_GENERATIONS,
    )

    validated["pmut"] = require_probability(
        validated.get("pmut"),
        label="Mutation probability",
    )

    validated["pcross"] = require_probability(
        validated.get("pcross"),
        label="Crossover probability",
    )

    return validated


def validate_partition_community_count(
    value: Any,
) -> int:
    return require_bounded_integer(
        value,
        label="Number of communities",
        minimum=1,
        maximum=MAX_PARTITION_COMMUNITIES,
    )


def validate_random_seed(
    value: Any,
) -> int:
    return require_bounded_integer(
        value,
        label="Random seed",
        minimum=0,
        maximum=MAX_RANDOM_SEED,
    )
