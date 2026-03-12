import base64
import os

import httpx
import truststore
from openai import OpenAI
import pydantic

truststore.inject_into_ssl()

os.environ['no_proxy'] = os.environ.get("api_url", "").replace("https://", "").split("/")[0]
API_URL = os.environ.get("api_url")
api_key = "{}".format(os.environ.get("API_KEY", "0"))
http_client = httpx.Client(verify=False)
client = OpenAI(
    base_url=API_URL,
    api_key=api_key,
    http_client=http_client,
)
models = client.models.list()
MODEL_ID = models.data[0].id
print(f"Using model: {MODEL_ID}")

class CityInfo(pydantic.BaseModel):
    city: str
    population: int
    

def encode_base64_content_from_file(file_path: str) -> str:
    """Encode a local file content to base64 format."""

    with open(file_path, "rb") as file:
        file_content = file.read()
        result = base64.b64encode(file_content).decode("utf-8")

    return result

def chat_think():
    messages = [
        {"role": "user", "content": "Type \"Das DCC hilft dir mit KI.\" backwards"},
    ]

    chat_response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=81920,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
        }, 
    )

    result = chat_response.choices[0].message.content
    reasoning = chat_response.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)

def chat_non_think():
    messages = [
        {"role": "user", "content": "Type \"Das DCC hilft dir mit KI.\" backwards"},
    ]

    chat_response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=32768,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "chat_template_kwargs": {"enable_thinking": False},
        }, 
    )
    result = chat_response.choices[0].message.content
    reasoning = chat_response.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)

    # Second test
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                         "url": "https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen3.5/demo/RealWorld/RealWorld-04.png"
                    }
                },
                {
                    "type": "text",
                    "text": "Where is this?"
                }
            ]
        }
    ]

    chat_response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=32768,
        temperature=0.7,
        top_p=0.8,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "chat_template_kwargs": {"enable_thinking": False},
        }, 
    )
    result = chat_response.choices[0].message.content
    reasoning = chat_response.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)

def chat_structured():
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"List 3 cities in Switzerland with population greater than 100,000. Return the result in a JSON array format, with each element containing the city name and its population. Follow this schema: {CityInfo.model_json_schema()}"
                }
            ]
        }
    ]

    chat_response = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "guided_json": CityInfo.model_json_schema(),
        },

    )
    result = chat_response.choices[0].message.content
    reasoning = chat_response.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)

def chat_structured_oai():
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Return a City in Spain with population greater than 100,000. Follow this schema: {CityInfo.model_json_schema()}"
                }
            ]
        }
    ]

    chat_response = client.chat.completions.parse(
        model=MODEL_ID,
        messages=messages,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        response_format=CityInfo,
        extra_body={
            "top_k": 20,
            "guided_decoding_backend": "outlines",
        },

    )
    result = chat_response.choices[0].message.content
    reasoning = chat_response.choices[0].message.reasoning
    parsed = chat_response.choices[0].message.parsed
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)
    print("Parsed output:\n", parsed)
    print("Is valid JSON:\n", CityInfo.model_validate(parsed))


def run_image():
    image_file = "example_data/city.jpg"
    image_base64 = encode_base64_content_from_file(image_file)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:video/jpg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": "Where is this?"
                }
            ]
        }
    ]

    response = client.chat.completions.create(
        model="Qwen/Qwen3.5-27B",
        messages=messages,
        max_tokens=81920,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
        }, 
    )
    result = response.choices[0].message.content
    reasoning = response.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output:\n", result)

def run_video() -> None:
    video_file = "example_data/shoes.mp4"
    video_base64 = encode_base64_content_from_file(video_file)

    ## Use base64 encoded video in the payload
    chat_completion_from_base64 = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this video?"},
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_base64}"},
                    },
                ],
            }
        ],
        model=MODEL_ID,
        max_tokens=81920,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
        }, 
    )

    result = chat_completion_from_base64.choices[0].message.content
    reasoning = chat_completion_from_base64.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output from base64 encoded video:\n", result)

def run_video_no_think() -> None:
    video_file = "example_data/output.mp4"
    video_base64 = encode_base64_content_from_file(video_file)

    ## Use base64 encoded video in the payload
    chat_completion_from_base64 = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this video?"},
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_base64}"},
                    },
                ],
            }
        ],
        model=MODEL_ID,
        max_tokens=81920,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
            "chat_template_kwargs": {"enable_thinking": False},
        }, 
    )

    result = chat_completion_from_base64.choices[0].message.content
    reasoning = chat_completion_from_base64.choices[0].message.reasoning
    print("Reasoning steps:\n", reasoning)
    print("Chat completion output from base64 encoded video:\n", result)


if __name__ == "__main__":
    print("=== Test Chat with thinking enabled ===")
    chat_think()
    print("=== Test Chat with thinking disabled ===")
    chat_non_think()
    print("=== Test Chat with structured output ===")
    chat_structured()
    print("=== Test Chat with structured output using OAI response format ===")
    chat_structured_oai()
    print("\n=== Test Image with thinking enabled ===")
    run_image()
    print("\n=== Test Video with thinking enabled ===")
    run_video()
    print("\n=== Test Video with thinking disabled ===")
    run_video_no_think()