import os
import base64
import io
from PIL import Image
import httpx
import truststore
from openai import OpenAI

truststore.inject_into_ssl()

# Configuration
API_URL = os.environ.get("api_url", "http://localhost:8000/v1")
API_KEY = os.environ.get("API_KEY", "none")
MODEL_NAME = "zai-org/GLM-OCR"
CUSTOM_PROMPT = "Recognize the text in the image and output in Markdown format. Preserve the original layout (headings/paragraphs/tables/formulas). Do not fabricate content that does not exist in the image."
os.environ['no_proxy'] = os.environ.get("API_URL", "").replace("https://", "").split("/")[0]

modes = {
    "text": "Text Recognition:",
    "formula": "Formula Recognition:",
    "table": "Table Recognition:"
}
MODE = "text"  # Change to "formula" or "table" as needed

def encode_image_to_base64(image_path: str) -> str:
    with Image.open(image_path) as img:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64_string = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64_string}"

def use_httpx(image_data_uri: str):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": CUSTOM_PROMPT,
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": modes[MODE]},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            }
        ],
    }
    
    with httpx.Client(timeout=30.0) as client:
        client.headers.update({"Authorization": f"Bearer {API_KEY}"})
        response = client.post(API_URL + "/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

def use_openai_sdk(image_data_uri: str):
    client = OpenAI(base_url=API_URL, api_key=API_KEY)
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CUSTOM_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            }
        ],
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    # Path to your document image or crop
    test_image = "example_data/example_image.jpg"
    test_image = "example_data/example_image_2.png"
    image_uri = encode_image_to_base64(test_image)

    print("--- Testing via HTTPX ---")
    print(use_httpx(image_uri))

    print("\n--- Testing via OpenAI SDK ---")
    print(use_openai_sdk(image_uri))