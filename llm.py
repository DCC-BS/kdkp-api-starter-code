
from openai import OpenAI
import truststore

truststore.inject_into_ssl()

API_URL = "http://localhost:9001/v1"

client = OpenAI(
    base_url=API_URL,
    api_key="token-abc123",
)

models = client.models.list()
MODEL_ID = models.data[0].id

def completition_chat():
    completion = client.chat.completions.create(
        model=MODEL_ID, messages=[{"role": "user", "content": "Hello!"}]
    )
    print(completion.choices[0].message)


def completition_create():
    completion = client.completions.create(model=MODEL_ID, prompt="Hy my name is")
    print(completion.choices[0].text)


if __name__ == "__main__":
    completition_chat()
    completition_create()
