import os

from openai import OpenAI
from PIL import Image

from utils.dots_ocr_utils import load_images_from_pdf, pil_image_to_base64
from utils.get_model import get_model_id
from utils.ocr_prompts import dict_promptmode_to_prompt


def inference_with_vllm(
    image: Image.Image,
    prompt: str,
    host="localhost",
    port=8000,
    temperature=0.1,
    top_p=0.9,
    max_completion_tokens=32768,
):
    api_url = f"https://{host}:{port}/v1"
    api_key = "{}".format(os.environ.get("API_KEY", "0"))
    client = OpenAI(api_key=api_key, base_url=api_url)
    model_name = get_model_id(api_key=api_key, api_url=api_url)
    messages = []
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": pil_image_to_base64(image)},
                },
                {
                    "type": "text",
                    "text": f"<|img|><|imgpad|><|endofimg|>{prompt}",
                },
            ],
        }
    )
    response = client.chat.completions.create(
        messages=messages,
        model=model_name,
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    image = Image.open("example_data/example_image.jpg")
    prompt = dict_promptmode_to_prompt["prompt_ocr"]
    response = inference_with_vllm(image, prompt)
    print(response)

    pdf_file = "example_data/example_pdf.pdf"
    pdf_images = load_images_from_pdf(pdf_file)
    for pdf_image in pdf_images:
        response = inference_with_vllm(pdf_image, prompt)
        print(response)
