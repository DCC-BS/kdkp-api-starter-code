
import os
from openai import OpenAI
import truststore

truststore.inject_into_ssl()

API_URL = os.environ.get("api_url")
client = OpenAI(
    base_url=API_URL,
    api_key="token-abc123",
)
models = client.models.list()
MODEL_ID = models.data[0].id

def completition_chat():
    completion = client.chat.completions.create(
        model=MODEL_ID, messages=[{"role": "user", "content": "Hello! Write me a very long poem please. /nothink"}],
        stream=True
    )
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content)
        else:
            print(chunk.created)


def completition_create():
    completion = client.completions.create(model=MODEL_ID, prompt="Hy my name is")
    print(completion.choices[0].text)


if __name__ == "__main__":
    completition_chat()
    completition_create()
