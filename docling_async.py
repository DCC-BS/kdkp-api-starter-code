"""Asynchronous conversion: submit a task, poll it, fetch the result.

Use the async endpoints whenever a conversion takes longer than a request
timeout, when several documents go in at once, or when the client cannot hold
a connection open. The synchronous endpoints give up after
DOCLING_SERVE_MAX_SYNC_WAIT seconds and answer 504.
"""

import json
import os

from utils.docling_client import (
    DOCLING_URL,
    HEADERS,
    client,
    fetch_result,
    file_source,
    form_data,
    http_source,
    poll_task,
    preview,
    submit_async,
)

PDF_URL = "https://arxiv.org/pdf/2501.17887"
SECOND_PDF_URL = "https://arxiv.org/pdf/2206.01062"
LOCAL_PDF = "example_data/example_pdf.pdf"


def async_source():
    """Queue one URL, poll until it finishes, then pull the document."""
    task_id = submit_async(
        "/convert/source/async",
        options={
            "to_formats": ["md"],
            "do_ocr": True,
            "ocr_preset": "glm-ocr-remote",
            "layout_custom_config": {"kind": "ppdoclayout-v3"},
        },
        sources=[http_source(PDF_URL)],
    )
    task = poll_task(task_id)
    if task["task_status"] != "success":
        print(f"task failed: {task.get('error_message') or task.get('failure')}")
        return task
    result = fetch_result(task_id)
    preview(result)
    return result


def async_many_sources():
    """Queue several documents as one task.

    `task_meta` then reports progress per document, so the poll loop can show
    3/7 rather than a single pending flag.
    """
    task_id = submit_async(
        "/convert/source/async",
        options={"to_formats": ["md"]},
        sources=[http_source(PDF_URL), http_source(SECOND_PDF_URL)],
    )
    task = poll_task(task_id)
    print(json.dumps(task, indent=2))
    # Two or more documents come back as a zip, so read the raw bytes.
    with client() as api:
        response = api.get(f"/result/{task_id}")
        response.raise_for_status()
        print(f"result content-type: {response.headers.get('content-type')}")
        with open("docling_result.zip", "wb") as handle:
            handle.write(response.content)
    print("wrote docling_result.zip")
    return task


def async_file_upload():
    """Same flow for a local file. The upload is multipart, the polling is not."""
    with client() as api, open(LOCAL_PDF, "rb") as handle:
        response = api.post(
            "/convert/file/async",
            data=form_data(
                {
                    "to_formats": ["md"],
                    "do_ocr": True,
                    "ocr_preset": "rapidocr",
                    "ocr_lang": ["de"],
                    "target_type": "inbody",
                }
            ),
            files={"files": (os.path.basename(LOCAL_PDF), handle)},
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
    print(f"Queued task {task_id}")
    poll_task(task_id)
    preview(fetch_result(task_id))
    return task_id


def async_with_callback():
    """Let docling-serve call a webhook instead of polling.

    The callback fires once the task completes. Polling still works, so a
    webhook plus a slow poll is a reasonable belt-and-braces setup.
    """
    with client() as api, open(LOCAL_PDF, "rb") as handle:
        response = api.post(
            "/convert/file/async",
            data=[
                ("to_formats", "md"),
                ("target_type", "inbody"),
                (
                    "callbacks",
                    json.dumps(
                        {
                            "url": "https://hook.example.com/docling",
                            "headers": {"Authorization": "Bearer hook-token"},
                        }
                    ),
                ),
            ],
            files={"files": (os.path.basename(LOCAL_PDF), handle)},
        )
        response.raise_for_status()
        print(response.json())
        return response.json()["task_id"]


def async_websocket():
    """Subscribe to task updates instead of polling.

    Needs the `websockets` package, which is not a dependency of this repo:
    `uv add websockets`.
    """
    from websockets.sync.client import connect

    task_id = submit_async(
        "/convert/source/async",
        options={"to_formats": ["md"]},
        sources=[http_source(PDF_URL)],
    )
    uri = f"{DOCLING_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/status/ws/{task_id}"
    with connect(uri, additional_headers=HEADERS) as socket:
        for raw in socket:
            payload = json.loads(raw)
            print(payload["message"], payload.get("task", {}).get("task_status"))
            if payload["message"] == "error":
                break
            if payload["message"] == "update" and payload["task"]["task_status"] in (
                "success",
                "failure",
            ):
                break
    preview(fetch_result(task_id))
    return task_id


def async_base64_source():
    """Async task over an inline base64 file rather than a URL or an upload."""
    task_id = submit_async(
        "/convert/source/async",
        options={"to_formats": ["md", "json"]},
        sources=[file_source(LOCAL_PDF)],
    )
    poll_task(task_id)
    preview(fetch_result(task_id))
    return task_id


EXAMPLES = {
    "source": async_source,
    "many-sources": async_many_sources,
    "file-upload": async_file_upload,
    "callback": async_with_callback,
    "websocket": async_websocket,
    "base64": async_base64_source,
}


if __name__ == "__main__":
    import sys

    selected = sys.argv[1:] or ["source", "many-sources", "file-upload", "base64"]
    for name in selected:
        if name not in EXAMPLES:
            print(f"Unknown example: {name}. Available: {', '.join(EXAMPLES)}")
            continue
        print(f"\n=== {name} ===")
        try:
            EXAMPLES[name]()
        except Exception as error:  # noqa: BLE001 - examples should not stop the run
            print(f"failed: {error}")
