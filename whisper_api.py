import openai
import bentoml

AUDIO_PATH = 'example_data/example_audio.mp3'
AUDIO_GERMAN_PATH = 'example_data/example_audio_german.mp3'
API_URL = 'http://localhost:9001'


def bento_transcribe():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            transcription = client.transcribe(file=AUDIO_PATH)
            print(transcription["text"])

def bento_transcribe_stream():
    pass

def bento_transcribe_task():
    pass

def bento_translate():
    pass

def bento_get_models():
    pass

def bento_get_model():
    pass

def openai_transcribe():
    audio_file= open(AUDIO_PATH, "rb")
    openai_client = openai.OpenAI(api_key="none", base_url=API_URL + "/v1")
    transcription = openai_client.audio.transcriptions.create(file=audio_file, model="large-v3")
    print(transcription.text)

if __name__ == "__main__":
    bento_transcribe()
    openai_transcribe()