from enum import Enum

from openai import OpenAI
from pydantic import BaseModel
import truststore

truststore.inject_into_ssl()

API_URL = "http://localhost:9001/v1"

client = OpenAI(
    base_url=API_URL,
    api_key="token-abc123",
)

def _get_model_id() -> str:
    models = client.models.list()
    return models.data[0].id

def structured_output_decode_by_choice():
    MODEL_ID = _get_model_id()
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "user", "content": "Classify this sentiment: vLLM is wonderful!"}
        ],
        extra_body={"guided_choice": ["positive", "negative"]},
    )
    print(completion.choices[0].message.content)


def structured_output_decode_by_regex():
    MODEL_ID = _get_model_id()
    prompt = (
        "Generate an email address for Alan Turing, who works in Enigma."
        "End in .com and new line. Example result:"
        "alan.turing@enigma.com\n"
    )

    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_body={"guided_regex": "\w+@\w+\.com\n", "stop": ["\n"]},
    )
    print(completion.choices[0].message.content)


def structured_output_json():
    MODEL_ID = _get_model_id()
    class CarType(str, Enum):
        sedan = "sedan"
        suv = "SUV"
        truck = "Truck"
        coupe = "Coupe"

    class CarDescription(BaseModel):
        brand: str
        model: str
        car_type: CarType

    json_schema = CarDescription.model_json_schema()

    prompt = (
        "Generate a JSON with the brand, model and car_type of"
        "the most iconic car from the 90's"
    )
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_body={"guided_json": json_schema},
    )
    print(completion.choices[0].message.content)


def structured_output_decode_by_grammar():
    MODEL_ID = _get_model_id()
    """It works by using a context free EBNF grammar"""
    simplified_sql_grammar = """
        ?start: select_statement

        ?select_statement: "SELECT " column_list " FROM " table_name

        ?column_list: column_name ("," column_name)*

        ?table_name: identifier

        ?column_name: identifier

        ?identifier: /[a-zA-Z_][a-zA-Z0-9_]*/
    """

    prompt = (
        "Generate an SQL query to show the 'username' and 'email'"
        "from the 'users' table."
    )
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_body={"guided_grammar": simplified_sql_grammar},
    )
    print(completion.choices[0].message.content)

if __name__ == "__main__":
    structured_output_decode_by_choice()
    structured_output_decode_by_regex()
    structured_output_json()
    structured_output_decode_by_grammar()
