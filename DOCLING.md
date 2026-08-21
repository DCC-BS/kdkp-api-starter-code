# Docling Serve

Document conversion and chunking against [dcc-docling-serve](https://github.com/DCC-BS/dcc-docling-serve),
a patched build of docling-serve 1.31.0 that adds two DCC plugins:

- **glm-ocr-remote**, OCR delegated to a vLLM-hosted GLM-OCR model
- **ppdoclayout-v3**, layout detection with PP-DocLayout-V3

Everything else is stock docling-serve, so the upstream
[usage docs](https://github.com/docling-project/docling-serve/blob/main/docs/usage.md)
apply, and the running server publishes its own schema at `/openapi.json`,
`/scalar` and `/docs`.

## Contents

- [Setup](#setup)
- [Scripts](#scripts)
- [Endpoints](#endpoints)
- [Pipelines](#pipelines)
- [OCR engines](#ocr-engines)
- [Layout engines](#layout-engines)
- [Picture description with Gemma 4](#picture-description-with-gemma-4)
- [Enrichments](#enrichments)
- [Inputs](#inputs)
- [Outputs](#outputs)
- [Async tasks](#async-tasks)
- [Chunking](#chunking)
- [Choosing a configuration](#choosing-a-configuration)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Setup

Add the docling endpoint to your `.env`:

```dotenv
API_KEY=your_api_key_here
docling_url=https://your-docling-host/v1
api_url=https://your-vllm-host/v1
vlm_model=
```

`docling_url` is the docling-serve API including the `/v1` prefix. `api_url` is
the vLLM endpoint used for image description; leave `vlm_model` empty to let the
scripts read the served model id from `/v1/models`.

Every request sends `Authorization: Bearer $API_KEY`. A bare docling-serve
instance uses `X-Api-Key` instead, so swap the header if you talk to one
directly rather than through the KDM gateway.

Then:

```sh
uv sync
uv run --env-file .env docling_usage.py
```

The curl examples below expect these in the shell:

```sh
export DOCLING_URL=https://your-docling-host/v1
export VLLM_URL=https://your-vllm-host/v1
export API_KEY=your_api_key_here
export GEMMA_MODEL=$(curl -sH "Authorization: Bearer $API_KEY" "$VLLM_URL/models" | jq -r '.data[0].id')
```

## Scripts

| File | What it covers |
| --- | --- |
| `utils/docling_client.py` | Shared HTTP client, source builders, task polling |
| `docling_usage.py` | Conversion: pipelines, OCR engines, layout, picture description, input and output formats |
| `docling_async.py` | Submit, poll, fetch, callbacks, websockets |
| `docling_chunking.py` | Hybrid and hierarchical chunking for RAG |

Each script runs all its examples, or one at a time:

```sh
uv run --env-file .env docling_usage.py glm-ocr+pp-doc-layout
uv run --env-file .env docling_chunking.py hybrid
```

## Endpoints

| Endpoint | Input | Blocking |
| --- | --- | --- |
| `POST /v1/convert/source` | JSON, URLs or base64 | yes |
| `POST /v1/convert/file` | multipart upload | yes |
| `POST /v1/convert/source/async` | JSON | no |
| `POST /v1/convert/file/async` | multipart upload | no |
| `POST /v1/chunk/{hybrid,hierarchical}/source` | JSON | yes |
| `POST /v1/chunk/{hybrid,hierarchical}/file` | multipart upload | yes |
| `POST /v1/chunk/{hybrid,hierarchical}/source/async` | JSON | no |
| `GET /v1/status/poll/{task_id}` | | |
| `WS /v1/status/ws/{task_id}` | | |
| `GET /v1/result/{task_id}` | | |
| `GET /health`, `GET /version` | | |

The blocking endpoints give up after `DOCLING_SERVE_MAX_SYNC_WAIT` seconds and
answer 504. Anything with OCR over more than a handful of pages belongs on the
async endpoints.

Set `"target": {"kind": "inbody"}` on JSON requests and `target_type=inbody` on
multipart ones. Omitting it lets the server pick, and a deployment with artifact
storage picks presigned URLs, which returns links instead of content.

## Pipelines

`pipeline` selects how pages become a document.

| Value | How it works | Use it when |
| --- | --- | --- |
| `standard` (default) | Layout model finds regions, OCR reads the bitmap ones, TableFormer reads tables | Almost always |
| `vlm` | One vision model reads whole pages and emits DocTags | Layout that defeats region detection, or when a single model is easier to reason about |
| `asr` | Speech recognition over audio and video | Media files |

The standard pipeline is the only one where the OCR and layout options below
apply. The VLM pipeline replaces both.

<details>
<summary>curl</summary>

```sh
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {"to_formats": ["md", "doctags"], "pipeline": "vlm", "vlm_pipeline_preset": "default"},
    "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
    "target": {"kind": "inbody"}
  }'
```

</details>

## OCR engines

Pick an engine with `ocr_preset` (the engine name), or configure one with
`ocr_custom_config` (a dict whose `kind` is the engine name). The two are
mutually exclusive. `ocr_engine` still works but is deprecated.

`do_ocr` turns OCR on, and `force_ocr` makes it replace any existing text layer.
Scans need `force_ocr` only when the PDF carries a bad text layer from an
earlier OCR pass.

### rapidocr (PP-OCRv6)

Runs on the docling-serve host, no second service involved. Fast, cheap, and
good on clean print. `lang` picks the recognizer: PP-OCRv6 covers about
52 language codes including `de` and `en`, while script-family names such as
`latin` or `cyrillic` route to PP-OCRv5 instead.

| Option | Default | Notes |
| --- | --- | --- |
| `lang` | `["chinese"]` | One language per run; only the first entry is used |
| `backend` | `onnxruntime` | Also `openvino`, `paddle`, `torch` |
| `text_score` | `0.5` | Detection confidence floor |
| `use_det`, `use_cls`, `use_rec` | unset | Turn individual stages off |

<details>
<summary>curl</summary>

```sh
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "to_formats": ["md"],
      "do_ocr": true,
      "force_ocr": true,
      "ocr_custom_config": {
        "kind": "rapidocr",
        "lang": ["de"],
        "backend": "onnxruntime",
        "text_score": 0.5
      }
    },
    "sources": [{"kind": "http", "url": "https://example.org/scan.pdf"}],
    "target": {"kind": "inbody"}
  }'
```

</details>

### glm-ocr-remote

Sends each page crop to a vLLM-hosted `zai-org/GLM-OCR` as an image, and gets
Markdown back with headings, tables and formulas intact. Much better than
RapidOCR on handwriting, stamps, poor scans and dense tables, and much slower,
since every crop is a generation call.

The server already knows its vLLM URL from `GLMOCR_REMOTE_OCR_API_URL`, so
`"ocr_preset": "glm-ocr-remote"` is usually all a request needs. Override
per request through `ocr_custom_config`:

| Option | Default | Notes |
| --- | --- | --- |
| `api_url` | env | vLLM chat completion URL |
| `model_name` | `zai-org/GLM-OCR` | |
| `prompt` | built-in | Sent with every crop |
| `scale` | `3.0` | Render scale; raise for small print |
| `max_image_pixels` | `4500000` | Scale is reduced to stay under this |
| `max_concurrent_requests` | `10` | Threads per page |
| `max_retries` | `3` | On 5xx and network errors |
| `timeout` | `120` | Seconds per crop |
| `lang` | `["en"]` | Language hint |

<details>
<summary>curl</summary>

```sh
# Engine by name, server defaults
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {"to_formats": ["md"], "do_ocr": true, "ocr_preset": "glm-ocr-remote"},
    "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
    "target": {"kind": "inbody"}
  }'

# Same engine, tuned for small print
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "to_formats": ["md"],
      "do_ocr": true,
      "force_ocr": true,
      "ocr_custom_config": {
        "kind": "glm-ocr-remote",
        "lang": ["de"],
        "scale": 3.5,
        "max_concurrent_requests": 8
      }
    },
    "sources": [{"kind": "http", "url": "https://example.org/scan.pdf"}],
    "target": {"kind": "inbody"}
  }'
```

</details>

### Other engines

`easyocr`, `tesseract`, `tesserocr` and `ocrmac` are part of upstream docling
and are available when the image ships them. `auto` lets the server choose.

## Layout engines

Layout detection decides what is a heading, a paragraph, a table or a figure,
and in what order they are read. Configure it with `layout_custom_config`.

### ppdoclayout-v3

PP-DocLayout-V3 runs locally on the docling-serve GPU. It holds up better than
the built-in model on multi-column pages, forms and government paperwork.

| Option | Default | Notes |
| --- | --- | --- |
| `model_name` | `PaddlePaddle/PP-DocLayoutV3_safetensors` | |
| `confidence_threshold` | `0.5` | Detection floor, 0.0 to 1.0 |
| `batch_size` | `8` | Lower it if the GPU runs out of memory |
| `create_orphan_clusters` | `true` | Keep elements no region claimed |
| `keep_empty_clusters` | `false` | |
| `skip_cell_assignment` | `false` | |

<details>
<summary>curl</summary>

```sh
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {
      "to_formats": ["md", "json"],
      "do_ocr": true,
      "force_ocr": true,
      "ocr_preset": "glm-ocr-remote",
      "layout_custom_config": {"kind": "ppdoclayout-v3", "batch_size": 8},
      "do_table_structure": true,
      "table_mode": "accurate"
    },
    "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
    "target": {"kind": "inbody"}
  }'
```

</details>

### Heading levels

PDFs carry no heading hierarchy, so docling flattens every heading to level 1
unless you ask for inference:

```json
{"do_pdf_heading_hierarchy": true}
```

It reads PDF bookmarks first, then outline numbering, then font style. Tune it
through `pdf_heading_hierarchy_options`. Worth turning on for anything you plan
to chunk, since chunk headings come from this.

## Picture description with Gemma 4

`do_picture_description` crops every figure and asks a vision model what it
shows. The answer goes into the document model as a picture annotation with
`"kind": "description"`, not into the Markdown.

Point it at the KDM Gemma 4 endpoint with `picture_description_custom_config`:

- `model_spec` describes the model. `default_repo_id` is the id docling reports.
- `engine_options` is the HTTP call. `engine_type: "api"` means an
  OpenAI-compatible chat completions endpoint. Everything in `params` goes
  straight into the request body, so `model` belongs there.
- `picture_area_threshold` skips small images. The default `0.05` drops most
  icons; lower it to `0.02` to catch inline diagrams.
- `concurrency` is how many pictures are described at once.

The server has to run with `DOCLING_SERVE_ENABLE_REMOTE_SERVICES=true`, or it
refuses outbound calls.

<details>
<summary>curl</summary>

```sh
cat <<EOF > /tmp/picdesc.json
{
  "options": {
    "to_formats": ["md", "json"],
    "image_export_mode": "embedded",
    "include_images": true,
    "do_picture_description": true,
    "picture_description_custom_config": {
      "model_spec": {
        "name": "Gemma 4",
        "default_repo_id": "${GEMMA_MODEL}",
        "prompt": "Describe this image in a few sentences.",
        "response_format": "markdown"
      },
      "engine_options": {
        "engine_type": "api",
        "url": "${VLLM_URL}/chat/completions",
        "headers": {"Authorization": "Bearer ${API_KEY}"},
        "params": {"model": "${GEMMA_MODEL}", "max_completion_tokens": 300, "temperature": 0.2},
        "timeout": 120,
        "concurrency": 4
      },
      "prompt": "Describe this figure for a reader who cannot see it. Name the chart type, the axes and the main trend.",
      "picture_area_threshold": 0.02,
      "scale": 2.0
    }
  },
  "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
  "target": {"kind": "inbody"}
}
EOF

curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/picdesc.json \
  | jq -r '.document.json_content.pictures[].annotations[]? | select(.kind == "description") | .text'
```

</details>

## Enrichments

Each flag loads another model, so turn on only what the output needs.

| Flag | What it adds |
| --- | --- |
| `do_table_structure` | Table cells and spans; on by default |
| `do_formula_enrichment` | LaTeX for formulas |
| `do_code_enrichment` | Language-tagged code blocks |
| `do_picture_classification` | A class label per picture |
| `do_chart_extraction` | Numeric series behind charts |
| `do_picture_description` | Natural-language figure descriptions |

`table_mode` is `accurate` by default; `fast` trades cell precision for speed.

## Inputs

Three ways to get a document in:

| Method | Shape | When |
| --- | --- | --- |
| HTTP source | `{"kind": "http", "url": "..."}` | The server can reach the URL |
| Base64 source | `{"kind": "file", "base64_string": "...", "filename": "a.pdf"}` | JSON-only clients |
| Multipart upload | `POST /v1/convert/file` with `files=@a.pdf` | Local files; base64 inflates the payload by a third |

Accepted formats include `pdf`, `docx`, `pptx`, `xlsx`, `html`, `md`, `csv`,
`image`, `epub`, `email`, `latex`, `audio` and `video`. Restrict them with
`from_formats` when you want a wrong upload rejected rather than parsed.

On multipart requests, nested configs travel as JSON strings:

<details>
<summary>curl</summary>

```sh
# base64 source, written to a file to dodge "argument list too long"
B64=$(base64 -w 0 example_data/example_pdf.pdf)
cat <<EOF > /tmp/body.json
{
  "options": {"to_formats": ["md"], "ocr_preset": "glm-ocr-remote"},
  "sources": [{"kind": "file", "base64_string": "${B64}", "filename": "example_pdf.pdf"}],
  "target": {"kind": "inbody"}
}
EOF
curl -X POST "$DOCLING_URL/convert/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/body.json

# multipart upload
curl -X POST "$DOCLING_URL/convert/file" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files=@example_data/example_pdf.pdf;type=application/pdf" \
  -F "to_formats=md" \
  -F "do_ocr=true" \
  -F "ocr_preset=glm-ocr-remote" \
  -F 'layout_custom_config={"kind":"ppdoclayout-v3","batch_size":8}' \
  -F "image_export_mode=embedded" \
  -F "do_pdf_heading_hierarchy=true" \
  -F "target_type=inbody"
```

</details>

## Outputs

`to_formats` accepts a list, and one conversion can return several renderings
at once. They all come from the same DoclingDocument.

| Format | Response field | Notes |
| --- | --- | --- |
| `md` | `md_content` | Default |
| `json` | `json_content` | The full document model; the only one carrying annotations, provenance and bounding boxes |
| `html`, `html_split_page` | `html_content` | |
| `text` | `text_content` | Plain text, no markup |
| `doctags` | `doctags_content` | The token format VLM pipelines emit |
| `doclang`, `dclx`, `vtt` | `doclang_content`, files | Document language format, archive, subtitles |
| `chunks` | `.chunks.jsonl` in the archive | Needs `chunking_options` and a file target such as `zip`; for chunks inline as JSON use the chunk endpoints |

Image handling is separate, through `image_export_mode`:

- `placeholder`, the default, drops image data entirely
- `embedded` inlines images as base64
- `referenced` writes files and links them

Ask for `include_page_images` when you want full-page renders, and set
`images_scale` (default `2.0`) to control resolution.

A single document with a single format comes back as JSON. Multiple documents,
or `"target": {"kind": "zip"}`, come back as a zip.

## Async tasks

Submit, poll, fetch. Task status moves through `pending`, `started`, then
`success`, `partial_success` or `failure`. While a task runs, `task_meta`
reports `num_processed` of `num_docs`.

```
POST /v1/convert/source/async  ->  {"task_id": "...", "task_status": "pending", "task_position": 3}
GET  /v1/status/poll/{task_id} ->  {"task_status": "started", "task_meta": {"num_docs": 2, "num_processed": 1}}
GET  /v1/result/{task_id}      ->  {"document": {...}, "status": "success", "processing_time": 41.2}
```

`GET /v1/result/{task_id}` before the task finishes answers 404, so poll first.
A failed task returns a `TaskFailureResult` with a category, a message and a
`retryable` flag rather than an HTTP error.

Two alternatives to polling:

- **Websocket.** Connect to `/v1/status/ws/{task_id}` and read `connection`,
  `update` and `error` messages until the status is terminal. Needs the
  `websockets` package.
- **Callbacks.** Pass a `callbacks` form field on the file endpoints, either a
  bare URL or a JSON `CallbackSpec` with headers. docling-serve calls it once
  the task completes.

<details>
<summary>curl</summary>

```sh
TASK=$(curl -sX POST "$DOCLING_URL/convert/source/async" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "options": {"to_formats": ["md"], "do_ocr": true, "ocr_preset": "glm-ocr-remote"},
    "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
    "target": {"kind": "inbody"}
  }' | jq -r .task_id)

until [ "$(curl -sH "Authorization: Bearer $API_KEY" \
  "$DOCLING_URL/status/poll/$TASK" | jq -r .task_status)" = "success" ]; do
  sleep 3
done

curl -sH "Authorization: Bearer $API_KEY" "$DOCLING_URL/result/$TASK" | jq -r .document.md_content

# webhook instead of polling
curl -X POST "$DOCLING_URL/convert/file/async" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files=@example_data/example_pdf.pdf" \
  -F "to_formats=md" \
  -F "target_type=inbody" \
  -F 'callbacks={"url":"https://hook.example.com/docling","headers":{"Authorization":"Bearer hook-token"}}'
```

</details>

## Chunking

docling chunks the document model rather than the Markdown, so every chunk keeps
its headings, page numbers and references back into the document. That metadata
is the point: it is what lets a RAG answer cite a page.

| Chunker | Splits on | Token budget |
| --- | --- | --- |
| `hierarchical` | Document structure | none |
| `hybrid` | Structure, then packs to a budget | yes |

Use hybrid for embedding pipelines and hierarchical when a later step does its
own packing.

Shared options:

| Option | Default | Notes |
| --- | --- | --- |
| `use_markdown_tables` | `false` | Markdown tables instead of triplets |
| `use_markdown_images` | `false` | Keep image references and add `has_image` to metadata |
| `image_placeholder` | `![IMAGE]` | Used when image serialization is off |
| `include_raw_text` | `false` | Return `raw_text` next to the contextualized `text` |

Hybrid adds:

| Option | Default | Notes |
| --- | --- | --- |
| `max_tokens` | from the tokenizer | Tokens per chunk |
| `tokenizer` | `sentence-transformers/all-MiniLM-L6-v2` | Match your embedding model |
| `merge_peers` | `true` | Glue short neighbouring chunks under the same heading |

Conversion options go in `convert_options`, so OCR engine, layout engine and
heading inference all apply to chunking too.

A chunk looks like this:

```json
{
  "filename": "2501.17887.pdf",
  "chunk_index": 7,
  "text": "Docling v2\nThe converter ...",
  "raw_text": "The converter ...",
  "num_tokens": 384,
  "headings": ["Docling v2"],
  "page_numbers": [3],
  "doc_items": ["#/texts/42", "#/texts/43"],
  "metadata": {}
}
```

<details>
<summary>curl</summary>

```sh
# hybrid chunking, sized for an embedding model
curl -X POST "$DOCLING_URL/chunk/hybrid/source" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "convert_options": {"do_ocr": true, "ocr_preset": "glm-ocr-remote", "do_pdf_heading_hierarchy": true},
    "chunking_options": {
      "max_tokens": 512,
      "tokenizer": "Qwen/Qwen3-Embedding-0.6B",
      "merge_peers": true,
      "use_markdown_tables": true,
      "include_raw_text": true
    },
    "sources": [{"kind": "http", "url": "https://arxiv.org/pdf/2501.17887"}],
    "include_converted_doc": false,
    "target": {"kind": "inbody"}
  }'

# hierarchical chunking of an uploaded file
curl -X POST "$DOCLING_URL/chunk/hierarchical/file" \
  -H "Authorization: Bearer $API_KEY" \
  -F "files=@example_data/example_pdf.pdf" \
  -F "convert_do_ocr=true" \
  -F "convert_ocr_preset=rapidocr" \
  -F "convert_ocr_lang=de" \
  -F "chunking_use_markdown_tables=true" \
  -F "include_converted_doc=false" \
  -F "target_type=inbody"
```

</details>

Note the form prefixes on the file endpoint: `convert_` for conversion options,
`chunking_` for chunker options.

## Choosing a configuration

| Documents | Configuration |
| --- | --- |
| Born-digital PDFs, Office files | `do_ocr: false`, default layout |
| Clean scans, high volume | `rapidocr` with `lang: ["de"]` |
| Poor scans, handwriting, stamps | `glm-ocr-remote` |
| Multi-column, forms, official paperwork | `ppdoclayout-v3` |
| Poor scans of multi-column paperwork | `glm-ocr-remote` plus `ppdoclayout-v3` |
| Documents whose figures carry meaning | add `do_picture_description` |
| Anything headed for RAG | add `do_pdf_heading_hierarchy`, then chunk hybrid |

Cost climbs down that table. GLM-OCR runs one generation call per page crop, so
a 40-page scan is a few hundred vLLM calls.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| 504 on a convert endpoint | Past `DOCLING_SERVE_MAX_SYNC_WAIT`. Use the async endpoint. |
| 422 `target kind ... is not allowed` | The deployment rejects the target. Send `{"kind": "inbody"}`. |
| Response has URLs instead of content | The server defaulted to a presigned target. Set the target explicitly. |
| 422 `must include a 'kind' field` | A `*_custom_config` arrived without `kind`. |
| 422 `Cannot specify both ocr_preset and ocr_custom_config` | Pick one. |
| `is not available on this system` | The engine is not installed in this image. Check `/openapi.json`. |
| Picture descriptions never appear | `DOCLING_SERVE_ENABLE_REMOTE_SERVICES` is off, or `picture_area_threshold` is above the figure size. |
| Empty descriptions, vLLM 400 | `model` is missing from `engine_options.params`. |
| vLLM 400 on large crops | vLLM needs `--max-num-batched-tokens 8192`; the default encoder cache is too small for an A4 page at scale 3. |
| GPU out of memory during layout | Lower `layout_custom_config.batch_size`. |
| 404 from `/v1/result/{task_id}` | The task has not finished. Poll first. |
| Every heading is level 1 | `do_pdf_heading_hierarchy` is off. |

## References

- [dcc-docling-serve](https://github.com/DCC-BS/dcc-docling-serve) and its [docs page](https://dcc-bs.github.io/documentation/docling/serve.html)
- [docling-glm-ocr](https://github.com/DCC-BS/docling-glm-ocr), [docs](https://dcc-bs.github.io/documentation/docling/glm-ocr.html)
- [docling-pp-doc-layout](https://github.com/DCC-BS/docling-pp-doc-layout), [docs](https://dcc-bs.github.io/documentation/docling/pp-doc-layout.html)
- [docling-serve upstream docs](https://github.com/docling-project/docling-serve/tree/main/docs)
