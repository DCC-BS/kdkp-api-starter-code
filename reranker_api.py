import os

import truststore

from utils.get_model import get_model_id

truststore.inject_into_ssl()
import json

import requests

DOCUMENTS = [
    "This is an example sentence. It is used for testing purposes. It has no real meaning.",
    "The quick brown fox jumps over the lazy dog. This is a pangram. It contains every letter of the alphabet.",
    "Embeddings are a powerful tool for natural language processing. They can be used for tasks like similarity search and clustering. This is just one example of their many applications.",
    "Machine learning is a rapidly growing field. There are many exciting new developments happening all the time. It is a great time to be involved in this area.",
    "Python is a popular programming language for machine learning. It has a large and active community. There are many excellent libraries available for machine learning in Python.",
    "The weather is beautiful today. The sun is shining and the birds are singing. I think I'll go for a walk in the park.",
    "I'm learning how to cook. I've been trying out new recipes every week. It's been a lot of fun.",
    "My favorite sport is basketball. I love the excitement of the game. It's always a close contest.",
    "I'm reading a great book right now. It's a mystery novel with a lot of twists and turns. I can't wait to see how it ends.",
    "I'm planning a trip to Europe next year. I'm going to visit several different countries. I'm really looking forward to it.",
]
QUERY = "What is machine learning?"

api_key = "{}".format(os.environ.get("API_KEY", "0"))
api_url = "http://localhost:8000/rerank"
openai_api_url = api_url.replace("/rerank", "/v1")
model_id = get_model_id(api_key=api_key, api_url=openai_api_url)
print(model_id)


def rerank():
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = {
        "model": model_id,
        "query": QUERY,
        "documents": DOCUMENTS,
    }
    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 200:
        print("Request successful!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)
    return response.json()


if __name__ == "__main__":
    rerank()
