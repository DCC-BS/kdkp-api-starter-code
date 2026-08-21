"""Document conversion with docling-serve 1.31.0 (dcc-docling-serve build).

Each function below is one conversion recipe. Run the file to execute them all,
or import a single one. See DOCLING.md for what the engines and options do.
"""

from utils.docling_client import (
    API_KEY,
    VLM_URL,
    convert_file,
    convert_source,
    file_source,
    http_source,
    preview,
    vlm_model_id,
)

PDF_URL = "https://arxiv.org/pdf/2501.17887"
LOCAL_PDF = "example_data/example_pdf.pdf"
LOCAL_IMAGE = "example_data/example_image.jpg"


def default_pipeline():
    """Standard pipeline with the built-in layout model and no OCR.

    The fastest option, and the right one for born-digital PDFs whose text
    layer is already correct.
    """
    result = convert_source(
        options={
            "to_formats": ["md"],
            "do_ocr": False,
            "do_table_structure": True,
            "table_mode": "accurate",
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def rapid_ocr():
    """RapidOCR with the PP-OCRv6 recognizer, running locally on the server.

    `lang` picks the recognizer. PP-OCRv6 covers about 52 language codes, so
    "de" and "en" both resolve to a v6 model. Script-family names such as
    "latin" or "cyrillic" fall back to PP-OCRv5 instead.
    """
    result = convert_source(
        options={
            "to_formats": ["md"],
            "do_ocr": True,
            "force_ocr": True,
            "ocr_custom_config": {
                "kind": "rapidocr",
                "lang": ["de"],
                "backend": "onnxruntime",
                "text_score": 0.5,
            },
        },
        sources=[file_source(LOCAL_IMAGE)],
    )
    preview(result)
    return result


def glm_ocr():
    """GLM-OCR, which sends each page crop to the vLLM server behind docling.

    Slower than RapidOCR and much better on handwriting, stamps, bad scans and
    dense tables. The server already knows its vLLM URL, so selecting the
    engine by name is enough.
    """
    result = convert_source(
        options={"to_formats": ["md"], "do_ocr": True, "ocr_preset": "glm-ocr-remote"},
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def glm_ocr_tuned():
    """Same engine, with the request overriding the server defaults.

    Raising `scale` helps on small print. Every field of GlmOcrRemoteOptions can
    go in here, and the server refuses unknown ones.
    """
    result = convert_source(
        options={
            "to_formats": ["md"],
            "do_ocr": True,
            "force_ocr": True,
            "ocr_custom_config": {
                "kind": "glm-ocr-remote",
                "lang": ["de"],
                "scale": 3.5,
                "max_concurrent_requests": 8,
                "prompt": (
                    "Recognize the text in the image and output it as Markdown. "
                    "Keep the original layout. Do not invent content."
                ),
            },
        },
        sources=[file_source(LOCAL_IMAGE)],
    )
    preview(result)
    return result


def pp_doc_layout():
    """PP-DocLayout-V3 instead of the built-in layout model.

    It finds reading order and region types on multi-column and form-like pages
    that the default model tends to scramble. Drop `batch_size` if the GPU runs
    out of memory.
    """
    result = convert_source(
        options={
            "to_formats": ["md"],
            "layout_custom_config": {
                "kind": "ppdoclayout-v3",
                "batch_size": 8,
                "confidence_threshold": 0.5,
            },
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def glm_ocr_with_pp_doc_layout():
    """Both DCC plugins together: PP-DocLayout finds the regions, GLM-OCR reads them.

    This is the highest-quality combination for scanned German documents, and
    the slowest.
    """
    result = convert_source(
        options={
            "to_formats": ["md", "json"],
            "do_ocr": True,
            "force_ocr": True,
            "ocr_preset": "glm-ocr-remote",
            "layout_custom_config": {"kind": "ppdoclayout-v3", "batch_size": 8},
            "do_table_structure": True,
            "table_mode": "accurate",
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def picture_description_gemma4():
    """Describe every figure with Gemma 4 on the KDKP vLLM endpoint.

    docling posts each cropped picture to an OpenAI-compatible chat endpoint and
    writes the answer back into the document as a picture annotation. The server
    needs DOCLING_SERVE_ENABLE_REMOTE_SERVICES=true for this to be allowed.
    """
    model = vlm_model_id()
    result = convert_source(
        options={
            "to_formats": ["md", "json"],
            "image_export_mode": "embedded",
            "include_images": True,
            "do_picture_description": True,
            "picture_description_custom_config": {
                "model_spec": {
                    "name": "Gemma 4",
                    "default_repo_id": model,
                    "prompt": "Describe this image in a few sentences.",
                    "response_format": "markdown",
                },
                "engine_options": {
                    "engine_type": "api",
                    "url": f"{VLM_URL}/chat/completions",
                    "headers": {"Authorization": f"Bearer {API_KEY}"},
                    # `params` goes straight into the chat completion body, so
                    # `model` has to be in here.
                    "params": {
                        "model": model,
                        "max_completion_tokens": 300,
                        "temperature": 0.2,
                    },
                    "timeout": 120,
                    "concurrency": 4,
                },
                "prompt": (
                    "Describe this figure for a reader who cannot see it. "
                    "Name the chart type, the axes and the main trend."
                ),
                "picture_area_threshold": 0.02,
                "scale": 2.0,
            },
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    # The descriptions land in the document model, not in the Markdown.
    document = result.get("document", {}).get("json_content") or {}
    for picture in document.get("pictures", []):
        for annotation in picture.get("annotations", []):
            if annotation.get("kind") == "description":
                print(f"picture description: {annotation['text'][:300]}")
    return result


def vlm_pipeline():
    """The VLM pipeline reads whole pages with one model instead of layout plus OCR.

    "default" resolves to whatever preset the server admin configured, so the
    request does not have to name a model.
    """
    result = convert_source(
        options={
            "to_formats": ["md", "doctags"],
            "pipeline": "vlm",
            "vlm_pipeline_preset": "default",
        },
        sources=[file_source(LOCAL_IMAGE)],
    )
    preview(result)
    return result


def all_output_formats():
    """One conversion, five renderings of the same DoclingDocument.

    `json_content` is the full document model. Everything else is derived from
    it, so ask for json when a downstream step needs structure.
    """
    result = convert_source(
        options={
            "to_formats": ["md", "json", "html", "text", "doctags"],
            "image_export_mode": "placeholder",
            "md_page_break_placeholder": "<!-- page -->",
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def upload_file():
    """Multipart upload. Nested configs travel as JSON strings in form fields.

    Use this for local files instead of base64 sources: it avoids inflating the
    payload by a third.
    """
    result = convert_file(
        LOCAL_PDF,
        options={
            "to_formats": ["md"],
            "do_ocr": True,
            "ocr_preset": "glm-ocr-remote",
            "layout_custom_config": {"kind": "ppdoclayout-v3"},
            "image_export_mode": "embedded",
            "do_pdf_heading_hierarchy": True,
        },
    )
    preview(result)
    return result


def page_range_and_timeout():
    """Convert pages 1 to 4 only, and give up after two minutes."""
    result = convert_source(
        options={
            "to_formats": ["md"],
            "page_range": [1, 4],
            "document_timeout": 120,
            "abort_on_error": True,
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


def enrichments():
    """Formula, code and chart enrichment on top of the standard pipeline.

    Each flag loads another model, so turn on only what the output needs.
    """
    result = convert_source(
        options={
            "to_formats": ["md"],
            "do_formula_enrichment": True,
            "do_code_enrichment": True,
            "do_picture_classification": True,
            "do_chart_extraction": True,
        },
        sources=[http_source(PDF_URL)],
    )
    preview(result)
    return result


EXAMPLES = {
    "default": default_pipeline,
    "rapid-ocr": rapid_ocr,
    "glm-ocr": glm_ocr,
    "glm-ocr-tuned": glm_ocr_tuned,
    "pp-doc-layout": pp_doc_layout,
    "glm-ocr+pp-doc-layout": glm_ocr_with_pp_doc_layout,
    "picture-description": picture_description_gemma4,
    "vlm-pipeline": vlm_pipeline,
    "output-formats": all_output_formats,
    "file-upload": upload_file,
    "page-range": page_range_and_timeout,
    "enrichments": enrichments,
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
