from typing import Any, Iterator

import pytest

from app import app
from src.config import APP_URL_PREFIX
from src.ui import ids


pytestmark = pytest.mark.integration


def _url(path: str) -> str:
    return f"{APP_URL_PREFIX}{path.lstrip('/')}"


def _component_ids(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        props = value.get("props")
        if isinstance(props, dict) and isinstance(props.get("id"), str):
            yield props["id"]

        for nested_value in value.values():
            yield from _component_ids(nested_value)

    elif isinstance(value, list):
        for item in value:
            yield from _component_ids(item)


@pytest.fixture
def client():
    return app.server.test_client()


def test_dash_index_is_served(client) -> None:
    response = client.get(APP_URL_PREFIX)

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert (
        "<title>STACI Dashboard</title>"
        in response.get_data(as_text=True)
    )


def test_dash_layout_contains_application_shell(client) -> None:
    response = client.get(_url("_dash-layout"))

    assert response.status_code == 200
    assert response.is_json

    component_ids = set(_component_ids(response.get_json()))
    assert {
        ids.URL,
        ids.PAGE_CONTENT,
        ids.NETWORK_STORE,
        ids.HYD_RUN_STORE,
        ids.PART_RUN_STORE,
        ids.FLUSH_RUN_STORE,
    }.issubset(component_ids)


def test_dash_dependencies_include_main_callbacks(client) -> None:
    response = client.get(_url("_dash-dependencies"))

    assert response.status_code == 200
    assert response.is_json

    dependencies = response.get_json()
    outputs = {
        dependency["output"]
        for dependency in dependencies
    }

    assert f"{ids.PAGE_CONTENT}.children" in outputs
    assert any(ids.HYD_RUN_STORE in output for output in outputs)
    assert any(ids.PART_RUN_STORE in output for output in outputs)


@pytest.mark.parametrize(
    ("path", "expected_class_name"),
    [
        ("", "page home-page"),
        ("network/load", "page load-page"),
        ("network/partitioning", "page partition-page"),
        ("analysis/hydraulic", "page hydro-page"),
        ("analysis/flushing", "page flush-page"),
    ],
)
def test_dash_renders_main_routes(
    client,
    path: str,
    expected_class_name: str,
) -> None:
    response = client.post(
        _url("_dash-update-component"),
        json={
            "output": f"{ids.PAGE_CONTENT}.children",
            "outputs": {
                "id": ids.PAGE_CONTENT,
                "property": "children",
            },
            "inputs": [
                {
                    "id": ids.URL,
                    "property": "pathname",
                    "value": _url(path),
                }
            ],
            "state": [],
            "changedPropIds": [f"{ids.URL}.pathname"],
        },
    )

    assert response.status_code == 200

    page = response.get_json()[
        "response"
    ][ids.PAGE_CONTENT]["children"]

    assert page["props"]["className"] == expected_class_name


def test_dash_serves_application_stylesheet(client) -> None:
    response = client.get(
        _url("assets/css/01_base.css")
    )

    assert response.status_code == 200
    assert response.content_type.startswith("text/css")
    assert ":root" in response.get_data(as_text=True)