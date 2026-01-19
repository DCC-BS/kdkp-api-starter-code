# KDM API Starter Code

## Contents

- [Initial Setup](#getting-started)
- [Embeddings API](#embeddings-api)
- [Reranker API](#reranker-api)
- [Whisper API](#whisper-api)
- [LLM API](#llm-api)
- [Structured Output](#structured-output)
- [Tool Use](#tool-use)
- [Dots OCR](#dots-ocr)
- [Notes](#notes)
- [License](#license)

This repository provides starter code to interact with:

- vLLM-compatible chat/completions endpoints (OpenAI client)
- Embeddings and reranking endpoints
- Whisper (audio transcription/translation) served via BentoML
- Simple OCR with images/PDFs routed to a VLM endpoint

## Brief Description of the Files

* **embeddings_api.py:** Generate embeddings for documents/queries using an OpenAI-compatible API (`encode_documents()`, `encode_queries()`).
* **reranker_api.py:** Rerank a set of documents for a query using a dedicated endpoint (`/rerank` on port 8002 by default), fetching the model ID from the OpenAI-compatible `/v1` on the same host (`rerank()`).
* **whisper_api.py:** Transcribe/translate audio via BentoML (`bento_transcribe()`, `bento_transcribe_stream()`, `bento_transcribe_task()`, `bento_translate()`), and via OpenAI-compatible client (`openai_transcribe()`).
* **llm.py:** Chat and text completion examples against an OpenAI-compatible API.
* **llm_structured_output.py:** Structured output examples (choice, regex, JSON schema, and EBNF grammar) against an OpenAI-compatible API.
* **llm_tool_use.py:** Tool-calling example including streamed tool call arguments.
* **dots_ocr.py:** Minimal OCR pipeline showing image/PDF ingestion and prompting a VLM endpoint.
* **pyproject.toml:** Project dependencies.
* **LICENSE:** MIT License file.

## Getting Started

1. **Install uv (package manager):**
   - macOS/Linux:
     - `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell):
     - `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`


2. **Install dependencies:**
   - `uv sync`

3. **Environment setup (.env):**
   - Rename `.env.example` to `.env`.
   - Open `.env` and set your API key:
     - `API_KEY=your_api_key_here`

4. **Configure the API URLs (if needed):**
  - The examples use defaults inside each script:
    - LLM and embeddings: `http://localhost:8000/v1`
    - Reranker: `http://localhost:8000/rerank` (internally uses `http://localhost:8000/v1` to fetch the model)
    - Whisper via BentoML: `http://localhost:9001` (OpenAI client uses `.../v1`)
   - Adjust the constants in the scripts if your endpoints differ.

5. **Run the example scripts:**
   - Embeddings: `uv run --env-file .env embeddings_api.py`
   - Reranker: `uv run --env-file .env reranker_api.py`
   - Whisper (BentoML): `uv run --env-file .env whisper_api.py`
   - LLM chat/completions: `uv run --env-file .env llm.py`
   - Structured output: `uv run --env-file .env llm_structured_output.py`
   - Tool use: `uv run --env-file .env llm_tool_use.py`
   - Dots OCR (image/PDF to VLM): `uv run --env-file .env dots_ocr.py`

## Features

<a id="embeddings-api"></a>
* **embeddings_api.py**
    * `encode_documents()`: Encodes a list of documents into embeddings.
    * `encode_queries()`: Encodes a list of queries into embeddings.

<a id="reranker-api"></a>
* **reranker_api.py**
    * `rerank()`: Reranks documents based on a given query by POSTing to `/rerank` (Bearer token via `API_KEY` header). Retrieves the model ID from `/v1` on the same host/port.

<a id="whisper-api"></a>
* **whisper_api.py**
    * `bento_transcribe()`: Transcribes an audio file.
    * `bento_transcribe_stream()`: Transcribes an audio file in streaming mode.
    * `bento_transcribe_task()`: Transcribes an audio file using asynchronous tasks.
    * `bento_translate()`: Translates an audio file.
    * `openai_transcribe()`:  Shows how to directly use the OpenAI API for transcription (for comparison).

* **llm_*.py**
    * <a id="llm-api"></a>`llm.py`: Chat and text completion usage with an OpenAI-compatible API.
    * <a id="structured-output"></a>`llm_structured_output.py`: Showcase for structured outputs (choice, regex, JSON schema, EBNF grammar).
    * <a id="tool-use"></a>`llm_tool_use.py`: Showcase for LLM tool use with streamed tool call arguments.

<a id="dots-ocr"></a>
* **dots_ocr.py**
    * Loads an image or PDF pages and queries a VLM endpoint for OCR-like tasks using prompts.
    * Available prompts (see `utils/ocr_prompts.py`):
        * `prompt_ocr`: Extract the text content from an image.
        * `prompt_layout_all_en`: Output layout elements as a single JSON object, including bbox, category, and text. Use LaTeX for formulas, HTML for tables, Markdown for other text; preserve original text and reading order.
        * `prompt_layout_only_en`: Output only layout bbox and category in JSON (no text content).
        * `prompt_grounding_ocr`: Extract text within a given bounding box `[x1, y1, x2, y2]`.

## Notes

* Whisper examples use `bentoml.SyncHTTPClient` to interact with the BentoML server.
* Update API URLs in the scripts if your endpoints differ from the defaults.
* Set `API_KEY` via your environment (see .env section) for all examples.
* Example media files are in the `example_data` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

If there are any questions, ask `dcc@bs.ch`.
