"""Chunking documents with docling-serve, for RAG pipelines.

docling-serve chunks the DoclingDocument, not the Markdown, so every chunk
keeps its headings, page numbers and item references. Two chunkers are
available: hierarchical splits along the document structure, hybrid splits the
same way and then packs the pieces to a token budget.
"""

import os

from utils.docling_client import (
    client,
    fetch_result,
    form_data,
    http_source,
    poll_task,
)

PDF_URL = "https://arxiv.org/pdf/2501.17887"
LOCAL_PDF = "example_data/example_pdf.pdf"

# Match this to the embedding model that will index the chunks.
TOKENIZER = "Qwen/Qwen3-Embedding-0.6B"


def show_chunks(result: dict, limit: int = 3) -> dict:
    chunks = result.get("chunks", [])
    print(f"{len(chunks)} chunks in {result.get('processing_time')}s")
    for chunk in chunks[:limit]:
        print(f"--- chunk {chunk['chunk_index']} ---")
        print(f"headings: {chunk.get('headings')}")
        print(f"pages: {chunk.get('page_numbers')} tokens: {chunk.get('num_tokens')}")
        print(chunk["text"][:400])
    return result


def chunk_source(chunker: str, chunking_options: dict, convert_options: dict) -> dict:
    """POST /v1/chunk/{hybrid|hierarchical}/source."""
    payload = {
        "convert_options": convert_options,
        "chunking_options": chunking_options,
        "sources": [http_source(PDF_URL)],
        "include_converted_doc": False,
        "target": {"kind": "inbody"},
    }
    with client() as api:
        response = api.post(f"/chunk/{chunker}/source", json=payload)
        response.raise_for_status()
        return response.json()


def hybrid_chunking():
    """Token-aware chunks sized for an embedding model.

    `max_tokens` defaults to whatever the tokenizer declares. `merge_peers`
    glues short neighbouring chunks under the same heading back together, which
    keeps one-line sections out of the index.
    """
    result = chunk_source(
        chunker="hybrid",
        chunking_options={
            "max_tokens": 512,
            "tokenizer": TOKENIZER,
            "merge_peers": True,
            "use_markdown_tables": True,
            "include_raw_text": True,
        },
        convert_options={"do_ocr": False},
    )
    return show_chunks(result)


def hierarchical_chunking():
    """One chunk per document node, with no token budget.

    Useful when the downstream step does its own packing, or when chunks must
    line up with sections exactly.
    """
    result = chunk_source(
        chunker="hierarchical",
        chunking_options={"use_markdown_tables": True, "include_raw_text": True},
        convert_options={"do_ocr": False},
    )
    return show_chunks(result)


def chunk_scanned_document():
    """Chunking runs on top of a conversion, so the OCR and layout options apply.

    Everything the convert endpoints accept goes into `convert_options`.
    """
    result = chunk_source(
        chunker="hybrid",
        chunking_options={"max_tokens": 512, "tokenizer": TOKENIZER},
        convert_options={
            "do_ocr": True,
            "force_ocr": True,
            "ocr_preset": "glm-ocr-remote",
            "layout_custom_config": {"kind": "ppdoclayout-v3"},
            "do_pdf_heading_hierarchy": True,
        },
    )
    return show_chunks(result)


def chunk_with_images():
    """Keep image references inside the chunks.

    Each chunk that contains an image gets `has_image` in its metadata, so an
    indexer can route those to a captioning step.
    """
    result = chunk_source(
        chunker="hybrid",
        chunking_options={
            "max_tokens": 512,
            "tokenizer": TOKENIZER,
            "use_markdown_images": True,
        },
        convert_options={"image_export_mode": "embedded", "include_images": True},
    )
    return show_chunks(result)


def chunk_file_upload():
    """POST /v1/chunk/hybrid/file.

    The form prefixes tell the two option sets apart: `convert_` for conversion
    options, `chunking_` for chunker options.
    """
    convert = form_data(
        {
            "do_ocr": True,
            "ocr_preset": "rapidocr",
            "ocr_lang": ["de"],
            "do_pdf_heading_hierarchy": True,
        }
    )
    chunking = form_data(
        {"max_tokens": 512, "tokenizer": TOKENIZER, "merge_peers": True}
    )
    data = {f"convert_{k}": v for k, v in convert.items()}
    data.update({f"chunking_{k}": v for k, v in chunking.items()})
    data["include_converted_doc"] = "false"
    data["target_type"] = "inbody"

    with client() as api, open(LOCAL_PDF, "rb") as handle:
        response = api.post(
            "/chunk/hybrid/file",
            data=data,
            files={"files": (os.path.basename(LOCAL_PDF), handle)},
        )
        response.raise_for_status()
        return show_chunks(response.json())


def chunk_async():
    """Chunking has the same async endpoints as conversion."""
    payload = {
        "convert_options": {"do_ocr": False},
        "chunking_options": {"max_tokens": 512, "tokenizer": TOKENIZER},
        "sources": [http_source(PDF_URL)],
        "target": {"kind": "inbody"},
    }
    with client() as api:
        response = api.post("/chunk/hybrid/source/async", json=payload)
        response.raise_for_status()
        task_id = response.json()["task_id"]
    print(f"Queued task {task_id}")
    poll_task(task_id)
    return show_chunks(fetch_result(task_id))


def chunks_as_output_format():
    """The convert endpoint can emit chunks as a file next to the document.

    `chunks` in `to_formats` writes a `.chunks.jsonl` per document, which only a
    file target can deliver, so this asks for a zip. Use it when one call should
    return the Markdown and the chunks together; use /v1/chunk/... when you want
    the chunks inline as JSON.
    """
    payload = {
        "options": {
            "to_formats": ["md", "chunks"],
            "chunking_options": {
                "chunker": "hybrid",
                "max_tokens": 512,
                "tokenizer": TOKENIZER,
            },
        },
        "sources": [http_source(PDF_URL)],
        "target": {"kind": "zip"},
    }
    with client() as api:
        response = api.post("/convert/source", json=payload)
        response.raise_for_status()
        with open("docling_chunks.zip", "wb") as handle:
            handle.write(response.content)
    print("wrote docling_chunks.zip (contains the markdown and a .chunks.jsonl)")
    return "docling_chunks.zip"


EXAMPLES = {
    "hybrid": hybrid_chunking,
    "hierarchical": hierarchical_chunking,
    "scanned": chunk_scanned_document,
    "images": chunk_with_images,
    "file-upload": chunk_file_upload,
    "async": chunk_async,
    "as-output-format": chunks_as_output_format,
}


if __name__ == "__main__":
    import sys

    selected = sys.argv[1:] or list(EXAMPLES)
    for name in selected:
        if name not in EXAMPLES:
            print(f"Unknown example: {name}. Available: {', '.join(EXAMPLES)}")
            continue
        print(f"\n=== {name} ===")
        try:
            EXAMPLES[name]()
        except Exception as error:  # noqa: BLE001 - examples should not stop the run
            print(f"failed: {error}")
