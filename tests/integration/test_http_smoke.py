from typing import Any, Iterator

import pytest

from app import app
from src.config import APP_URL_PREFIX
from src.ui import ids
from src.ui.paths import app_path
from src.ui.sidebar import WORDPRESS_HOME_URL


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


def _component_links(
    value: Any,
) -> Iterator[tuple[str, str | None]]:
    if isinstance(value, dict):
        props = value.get("props")

        if isinstance(props, dict):
            href = props.get("href")
            target = props.get("target")

            if isinstance(href, str):
                yield (
                    href,
                    target if isinstance(target, str) else None,
                )

        for nested_value in value.values():
            yield from _component_links(nested_value)

    elif isinstance(value, list):
        for item in value:
            yield from _component_links(item)


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
    assert any(ids.FLUSH_RUN_STORE in output for output in outputs)
    assert (f"{ids.FLUSH_NETWORK_GRAPH}.figure" in outputs)


@pytest.mark.parametrize(
    ("run_store_id", "run_status_id", "run_button_id"),
    [
        (
            ids.HYD_RUN_STORE,
            ids.HYD_RUN_STATUS,
            ids.HYD_RUN_BUTTON,
        ),
        (
            ids.PART_RUN_STORE,
            ids.PART_RUN_STATUS,
            ids.PART_RUN_BUTTON,
        ),
        (
            ids.FLUSH_RUN_STORE,
            ids.FLUSH_RUN_STATUS,
            ids.FLUSH_RUN_BUTTON,
        ),
    ],
)
def test_solver_runs_use_background_callbacks(
    client,
    run_store_id: str,
    run_status_id: str,
    run_button_id: str,
) -> None:
    response = client.get(
        _url("_dash-dependencies")
    )

    assert response.status_code == 200
    assert response.is_json

    matching_callbacks = [
        dependency
        for dependency in response.get_json()
        if (
            run_store_id in dependency["output"]
            and run_status_id in dependency["output"]
        )
    ]

    assert len(matching_callbacks) == 1

    callback = matching_callbacks[0]
    assert callback.get("background")

    running = callback.get("running")
    assert running is not None

    disabled_output = f"{run_button_id}.disabled"

    assert running["running"][disabled_output] is True
    assert running["runningOff"][disabled_output] is False


@pytest.mark.parametrize(
    (
        "path",
        "expected_class_name",
        "expected_component_ids",
    ),
    [
        (
            "",
            "page load-page",
            (),
        ),
        (
            "network/load",
            "page load-page",
            (
                ids.UPLOAD_INP,
                ids.ACTIVE_MODEL_SUMMARY,
                ids.NETWORK_GRAPH,
                ids.NODE_COLOR_MIN,
                ids.NODE_COLOR_MAX,
                ids.LINK_COLOR_MIN,
                ids.LINK_COLOR_MAX,
                ids.NETWORK_LINE_WIDTH,
                ids.NETWORK_MARKER_SIZE,
                ids.NETWORK_HIDE_NODES,
            ),
        ),
        (
            "analysis/partitioning",
            "page partition-page",
            (
                ids.PART_ACTIVE_MODEL_SUMMARY,
                ids.PART_RUN_BUTTON,
                ids.PART_RUN_STATUS,
                ids.PART_NETWORK_GRAPH,
                ids.PART_LINE_WIDTH,
                ids.PART_MARKER_SIZE,
                ids.PART_HIDE_NODES,
            ),
        ),
        (
            "analysis/hydraulic",
            "page hydro-page",
            (
                ids.HYD_ACTIVE_MODEL_SUMMARY,
                ids.HYD_RUN_BUTTON,
                ids.HYD_RUN_STATUS,
                ids.HYD_NETWORK_GRAPH,
                ids.HYD_NODE_COLOR_MIN,
                ids.HYD_NODE_COLOR_MAX,
                ids.HYD_LINK_COLOR_MIN,
                ids.HYD_LINK_COLOR_MAX,
                ids.HYD_LINE_WIDTH,
                ids.HYD_MARKER_SIZE,
                ids.HYD_HIDE_NODES,
            ),
        ),
        (
            "analysis/flushing",
            "page flush-page",
            (
                ids.FLUSH_ACTIVE_MODEL_SUMMARY,
                ids.FLUSH_RUN_BUTTON,
                ids.FLUSH_RUN_STATUS,
                ids.FLUSH_RESULTS,
            ),
        ),
    ],
)
def test_dash_renders_main_routes(
    client,
    path: str,
    expected_class_name: str,
    expected_component_ids: tuple[str, ...],
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

    component_ids = set(_component_ids(page))

    assert set(expected_component_ids).issubset(
        component_ids
    )


def test_dash_serves_application_stylesheet(client) -> None:
    response = client.get(
        _url("assets/css/01_base.css")
    )

    assert response.status_code == 200
    assert response.content_type.startswith("text/css")
    assert ":root" in response.get_data(as_text=True)
