from pathlib import Path

import pytest

from src.services.partition_runner import parse_membership


def write_membership(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "membership.txt"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_membership_returns_nodes_and_community_counts(
    tmp_path: Path,
) -> None:
    path = write_membership(
        tmp_path,
        """
        STACI split output
        n_nodes : 5

        #0; J1; J2;
        #1; J3;
        ignored diagnostic line
        #3; J4; J5;
        """,
    )

    membership = parse_membership(path)

    assert membership.n_nodes == 5
    assert membership.node_community == {
        "J1": 0,
        "J2": 0,
        "J3": 1,
        "J4": 3,
        "J5": 3,
    }
    assert membership.n_community_members == {
        0: 2,
        1: 1,
        3: 2,
    }
    assert membership.n_communities == 3


def test_parse_membership_rejects_missing_file(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing-membership.txt"

    with pytest.raises(FileNotFoundError, match="Membership file not found"):
        parse_membership(missing_path)


def test_parse_membership_rejects_missing_node_count(
    tmp_path: Path,
) -> None:
    path = write_membership(
        tmp_path,
        "#0; J1; J2;\n",
    )

    with pytest.raises(ValueError, match="Could not find n_nodes"):
        parse_membership(path)


@pytest.mark.parametrize(
    ("declared_count", "community_lines"),
    [
        (3, "#0; J1; J2;\n"),
        (1, "#0; J1; J2;\n"),
    ],
    ids=["too-few-parsed-nodes", "too-many-parsed-nodes"],
)
def test_parse_membership_rejects_node_count_mismatch(
    tmp_path: Path,
    declared_count: int,
    community_lines: str,
) -> None:
    path = write_membership(
        tmp_path,
        f"n_nodes : {declared_count}\n{community_lines}",
    )

    with pytest.raises(ValueError, match="Membership node count mismatch"):
        parse_membership(path)


def test_parse_membership_rejects_node_in_multiple_communities(
    tmp_path: Path,
) -> None:
    path = write_membership(
        tmp_path,
        """
        n_nodes : 2
        #0; J1; J2;
        #1; J2;
        """,
    )

    with pytest.raises(
        ValueError,
        match="Node 'J2' appears in multiple communities",
    ):
        parse_membership(path)