import json
import os
import time

import bentoml
import openai
import truststore

truststore.inject_into_ssl()

AUDIO_PATH = "example_data/example_audio.mp3"
AUDIO_GERMAN_PATH = "example_data/example_audio_german.mp3"
API_URL = "http://localhost:9001"

api_key = "{}".format(os.environ.get("API_KEY", "0"))


def bento_transcribe():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            transcription = client.transcribe(file=AUDIO_PATH)
            transcription = json.loads(transcription)
            print(transcription["text"])


def bento_transcribe_stream():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            for chunk in client.streaming_transcribe(file=AUDIO_PATH):
                print(chunk)


def bento_transcribe_task():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            task = client.task_transcribe.submit(file=AUDIO_PATH)
            print("Task submitted, ID: ", task.id)

            done = False
            while not done:
                status = task.get_status()
                if status.value == "success":
                    print("The task runs successfully. The result is: ")
                    transcription = json.loads(task.get())
                    print(transcription["text"])
                    done = True
                elif status.value == "failure":
                    print("The task run failed.")
                    done = True
                else:
                    print("The task is still running.")
                    time.sleep(5)


def bento_translate():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            translation = client.translate(file=AUDIO_GERMAN_PATH)
            translation = json.loads(translation)
            print(translation["text"])


def openai_transcribe():
    audio_file = open(AUDIO_PATH, "rb")
    openai_client = openai.OpenAI(api_key=api_key, base_url=API_URL + "/v1")
    transcription = openai_client.audio.transcriptions.create(
        file=audio_file, model="large-v3"
    )
    print(transcription.text)


if __name__ == "__main__":
    bento_transcribe()
    bento_transcribe_stream()
    bento_transcribe_task()
    bento_translate()
    openai_transcribe()
