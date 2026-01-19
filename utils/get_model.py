from openai import OpenAI


def get_model_id(api_key: str, api_url: str) -> str:
    client = OpenAI(api_key=api_key, base_url=api_url)
    models = client.models.list()
    return models.data[0].id
