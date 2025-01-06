# KDM API Starter Code

This repository provides starter code for interacting with a BentoML API serving OpenAI's Whisper model for audio transcription and translation.
Additionaly, there is a starter code for interacting with an embeddings API.

## Contents

* **embeddings_api.py:**  Example usage of a BentoML API for generating embeddings from text.
* **whisper_api.py:** Example usage of a BentoML API for transcribing and translating audio files using OpenAI's Whisper model.
* **pyproject.toml:** Project dependencies.
* **LICENSE:** MIT License file.

## Getting Started

1. **Configure the URLs:**
   -  Make sure you have the correct API URLs in the .py file

2. **Run the example scripts:**
   - Execute `uv run embeddings_api.py` to see how to generate embeddings and perform reranking with the BentoML API.
   - Execute `uv run whisper_api.py` to see how to transcribe and translate audio files using the BentoML API.

## Features

* **embeddings_api.py**
    *  `bento_encode_documents()`:  Encodes a list of documents into embeddings.
    *  `bento_encode_queries()`: Encodes a list of queries into embeddings.
    *  `bento_rerank()`:  Reranks documents based on a given query.

* **whisper_api.py**
    * `bento_transcribe()`: Transcribes an audio file.
    * `bento_transcribe_stream()`: Transcribes an audio file in streaming mode.
    * `bento_transcribe_task()`: Transcribes an audio file using asynchronous tasks.
    * `bento_translate()`: Translates an audio file.
    * `openai_transcribe()`:  Shows how to directly use the OpenAI API for transcription (for comparison).

## Notes

* This code uses `bentoml.SyncHTTPClient` to interact with the BentoML server.
* Make sure to update `API_URL` in both scripts to match the address of your BentoML server.
* You'll need an OpenAI API key to use the `openai_transcribe()` function.
* The example audio files are assumed to be in an `example_data` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
