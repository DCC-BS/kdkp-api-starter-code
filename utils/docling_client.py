"""Shared helpers for the Docling Serve example scripts.

Targets docling-serve 1.31.0 as shipped in ghcr.io/dcc-bs/dcc-docling-serve,
which adds the glm-ocr-remote OCR engine and the ppdoclayout-v3 layout engine.
"""

import base64
import json
import os
import time
from typing import Any

import httpx
import truststore

truststore.inject_into_ssl()

# Base URL of the docling-serve API, including the /v1 prefix.
DOCLING_URL = os.environ.get("docling_url", "http://localhost:5001/v1").rstrip("/")
API_KEY = os.environ.get("API_KEY", "none")

# Endpoint of the vLLM server used for image description (Gemma 4).
VLM_URL = os.environ.get("api_url", "http://localhost:8000/v1").rstrip("/")

os.environ["no_proxy"] = ",".join(
    part
    for part in (
        os.environ.get("no_proxy", ""),
        DOCLING_URL.split("//")[-1].split("/")[0],
        VLM_URL.split("//")[-1].split("/")[0],
    )
    if part
)

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Long enough for a GLM-OCR run over a multi-page PDF.
TIMEOUT = httpx.Timeout(600.0, connect=10.0)


def client() -> httpx.Client:
    return httpx.Client(base_url=DOCLING_URL, headers=HEADERS, timeout=TIMEOUT)


def http_source(url: str) -> dict[str, Any]:
    """Source item that makes docling-serve download the document itself."""
    return {"kind": "http", "url": url}


def file_source(path: str) -> dict[str, Any]:
    """Source item that carries the file inline as base64."""
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode()
    return {
        "kind": "file",
        "base64_string": encoded,
        "filename": os.path.basename(path),
    }


def form_data(options: dict[str, Any]) -> dict[str, Any]:
    """Encode options for multipart requests.

    Form fields carry strings only, so nested configs go over the wire as JSON
    and booleans as "true"/"false". docling-serve decodes both server-side.
    """
    encoded: dict[str, Any] = {}
    for key, value in options.items():
        if isinstance(value, bool):
            encoded[key] = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            encoded[key] = json.dumps(value)
        else:
            encoded[key] = value
    return encoded


def convert_source(options: dict[str, Any], sources: list[dict[str, Any]]) -> dict:
    """POST /v1/convert/source - synchronous conversion of URLs or base64 files."""
    payload = {
        "options": options,
        "sources": sources,
        # Without this the server picks its own default target, which is a
        # presigned URL when artifact storage is configured.
        "target": {"kind": "inbody"},
    }
    with client() as api:
        response = api.post("/convert/source", json=payload)
        response.raise_for_status()
        return response.json()


def convert_file(path: str, options: dict[str, Any]) -> dict:
    """POST /v1/convert/file - synchronous conversion of an uploaded file."""
    with client() as api, open(path, "rb") as handle:
        response = api.post(
            "/convert/file",
            data=form_data({**options, "target_type": "inbody"}),
            files={"files": (os.path.basename(path), handle)},
        )
        response.raise_for_status()
        return response.json()


def submit_async(
    endpoint: str,
    options: dict[str, Any],
    sources: list[dict[str, Any]],
) -> str:
    """Queue a conversion and return its task id.

    `endpoint` is "/convert/source/async" or "/convert/file/async".
    """
    payload = {"options": options, "sources": sources, "target": {"kind": "inbody"}}
    with client() as api:
        response = api.post(endpoint, json=payload)
        response.raise_for_status()
        task = response.json()
    print(f"Queued task {task['task_id']} at position {task.get('task_position')}")
    return task["task_id"]


def poll_task(task_id: str, interval: float = 2.0) -> dict:
    """GET /v1/status/poll/{task_id} until the task leaves the queue."""
    with client() as api:
        while True:
            response = api.get(f"/status/poll/{task_id}")
            response.raise_for_status()
            task = response.json()
            meta = task.get("task_meta") or {}
            print(
                f"  status={task['task_status']}"
                f" position={task.get('task_position')}"
                f" processed={meta.get('num_processed')}/{meta.get('num_docs')}"
            )
            if task["task_status"] in ("success", "failure", "partial_success"):
                return task
            time.sleep(interval)


def fetch_result(task_id: str) -> dict:
    """GET /v1/result/{task_id} once the task has finished."""
    with client() as api:
        response = api.get(f"/result/{task_id}")
        response.raise_for_status()
        return response.json()


def preview(result: dict, chars: int = 600) -> None:
    """Print the status line and the head of every populated output format."""
    document = result.get("document", {})
    print(f"status={result.get('status')} time={result.get('processing_time')}s")
    for key in (
        "md_content",
        "text_content",
        "html_content",
        "doctags_content",
        "doclang_content",
    ):
        content = document.get(key)
        if content:
            print(f"--- {key} ---")
            print(content[:chars])
    if document.get("json_content"):
        body = document["json_content"]
        print(f"--- json_content --- {len(body.get('texts', []))} text items")
    for error in result.get("errors", []):
        print(f"error: {error}")


def vlm_model_id() -> str:
    """Model id to send to the vLLM server for picture description.

    Set `vlm_model` in .env to pin it, otherwise the first model the endpoint
    lists wins. Each KDKP vLLM endpoint serves exactly one model.
    """
    pinned = os.environ.get("vlm_model")
    if pinned:
        return pinned
    with httpx.Client(headers=HEADERS, timeout=30.0) as api:
        response = api.get(f"{VLM_URL}/models")
        response.raise_for_status()
        return response.json()["data"][0]["id"]
