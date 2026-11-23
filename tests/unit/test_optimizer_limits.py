import pytest

from src.staci.optimizer_limits import (
    MAX_OPTIMIZER_GENERATIONS,
    MAX_OPTIMIZER_POPULATION,
    MAX_PARTITION_COMMUNITIES,
    MAX_RANDOM_SEED,
    require_bounded_integer,
    require_probability,
    validate_optimizer_settings,
    validate_partition_community_count,
    validate_random_seed,
)


def test_validate_optimizer_settings_accepts_limits() -> None:
    settings = validate_optimizer_settings(
        {
            "popsize": MAX_OPTIMIZER_POPULATION,
            "ngen": MAX_OPTIMIZER_GENERATIONS,
            "pmut": 0.0,
            "pcross": 1.0,
        },
        minimum_population=2,
    )

    assert settings == {
        "popsize": MAX_OPTIMIZER_POPULATION,
        "ngen": MAX_OPTIMIZER_GENERATIONS,
        "pmut": 0.0,
        "pcross": 1.0,
    }


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        (
            "popsize",
            MAX_OPTIMIZER_POPULATION + 1,
            "Population size",
        ),
        (
            "ngen",
            MAX_OPTIMIZER_GENERATIONS + 1,
            "Generation count",
        ),
        (
            "pmut",
            -0.01,
            "Mutation probability",
        ),
        (
            "pcross",
            1.01,
            "Crossover probability",
        ),
    ],
)
def test_validate_optimizer_settings_rejects_invalid_values(
    field: str,
    value: float,
    expected_message: str,
) -> None:
    settings = {
        "popsize": 20,
        "ngen": 50,
        "pmut": 0.2,
        "pcross": 0.8,
    }
    settings[field] = value

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        validate_optimizer_settings(
            settings,
            minimum_population=2,
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        1.5,
        float("nan"),
        float("inf"),
    ],
)
def test_require_bounded_integer_rejects_non_integer_values(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        require_bounded_integer(
            value,
            label="Value",
            minimum=1,
            maximum=10,
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        -0.1,
        1.1,
        float("nan"),
        float("inf"),
    ],
)
def test_require_probability_rejects_invalid_values(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        require_probability(
            value,
            label="Probability",
        )


def test_partition_community_limit() -> None:
    assert (
        validate_partition_community_count(MAX_PARTITION_COMMUNITIES)
        == MAX_PARTITION_COMMUNITIES
    )

    with pytest.raises(
        ValueError,
        match="Number of communities",
    ):
        validate_partition_community_count(MAX_PARTITION_COMMUNITIES + 1)


def test_random_seed_limit() -> None:
    assert validate_random_seed(0) == 0
    assert validate_random_seed(MAX_RANDOM_SEED) == MAX_RANDOM_SEED

    with pytest.raises(
        ValueError,
        match="Random seed",
    ):
        validate_random_seed(MAX_RANDOM_SEED + 1)
