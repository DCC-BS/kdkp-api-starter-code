import bentoml
import numpy as np
import typing as t
import truststore

truststore.inject_into_ssl()

API_URL = 'http://localhost:50001'

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
    "I'm planning a trip to Europe next year. I'm going to visit several different countries. I'm really looking forward to it."
]
QUERIES = [
    "What is machine learning?",
    "Tell me about Python.",
    "Sports and hobbies",
    "Weather forecast"
]

def bento_encode_documents():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            embeddings : np.ndarray = client.encode_documents(documents=DOCUMENTS)
            print(embeddings.shape)
            print(embeddings)

def bento_encode_queries():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            embeddings : np.ndarray = client.encode_queries(queries=QUERIES)
            print(embeddings.shape)
            print(embeddings)

def bento_rerank():
    with bentoml.SyncHTTPClient(API_URL) as client:
        if client.is_ready():
            ranks: t.Dict = client.rerank(documents=DOCUMENTS, query=QUERIES[0])
            print(ranks)


if __name__ == "__main__":
    bento_encode_documents()
    bento_encode_queries()
    bento_rerank()