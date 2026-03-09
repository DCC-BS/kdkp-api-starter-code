import os
import httpx
import truststore

truststore.inject_into_ssl()

# Configuration
API_URL = os.environ.get("api_url", "http://localhost:8000/v1")
API_KEY = os.environ.get("API_KEY", "none")
os.environ['no_proxy'] = os.environ.get("API_URL", "").replace("https://", "").split("/")[0]
SOURCE_URL = "https://arxiv.org/pdf/2501.17887"
SOURCE_IMG = "example_data/example_image.jpg"

def convert_document(options: dict, description: str):
    """Sends a conversion request to Docling Serve with specific plugin options."""
    payload = {
        "options": options,
        "sources": [{"kind": "http", "url": SOURCE_URL}]
    }

    print(f"--- Testing: {description} ---")
    
    with httpx.Client(timeout=60.0) as client:
        client.headers.update({"Authorization": f"Bearer {API_KEY}"})
        try:
            response = client.post(f"{API_URL}/convert/source", json=payload)
            response.raise_for_status()
            
            # The API returns the converted document structure
            result = response.json()
            print(result)
            print("Status: Success")
            # Return a snippet of the result for verification
            return result
        except httpx.HTTPStatusError as e:
            print(f"Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Connection Error: {e}")

def convert_file(file_path: str, description: str, custom_options: dict = None):
    """Sends a conversion request to Docling Serve with specific plugin options."""
    data_payload = {
        "target_type": "inbody",
        "to_formats": "md",
        "image_export_mode": "embedded",
        "do_ocr": "true",
        "ocr_engine": "glm-ocr-remote",  # Using your custom plugin
        "pipeline": "standard",
        "do_table_structure": "true",
        "include_images": "true",
        "layout_custom_config.kind": "ppdoclayout-v3", # Using your custom layout plugin
        "vlm_pipeline_preset": "default",
    }
    endpoint = f"{API_URL}/convert/file"

    # Merge any specific overrides (like the complex VLM/Picture description JSONs)
    if custom_options:
        data_payload.update(custom_options)

    print(f"--- Testing: {description} ---")
    
    with httpx.Client(timeout=60.0) as client:
        client.headers.update({"Authorization": f"Bearer {API_KEY}"})
        try:
            with open(file_path, "rb") as f:
                files = {"files": (os.path.basename(file_path), f)}
                
                response = client.post(
                    endpoint, 
                    data=data_payload, 
                    files=files
                )
                
            response.raise_for_status()
            print("Status: Success")
            print(response.json())
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Connection Error: {e}")

if __name__ == "__main__":
    
    # 1. Using only GLM-OCR as the OCR engine
    glm_only_options = {
        "ocr_engine": "glm-ocr-remote"
    }
    convert_document(glm_only_options, "GLM-OCR Engine Only")

    # 2. Using only PP-DocLayout as the layout engine
    pp_layout_options = {
        "layout_custom_config": {"kind": "ppdoclayout-v3"}
    }
    convert_document(pp_layout_options, "PP-DocLayout Engine Only")

    # 3. Combined: Both GLM-OCR and PP-DocLayout
    combined_options = {
        "ocr_engine": "glm-ocr-remote",
        "layout_custom_config": {"kind": "ppdoclayout-v3"}
    }
    convert_document(combined_options, "Combined GLM-OCR + PP-DocLayout")

    # 4. Testing file upload with both plugins
    convert_file(SOURCE_IMG, "Combined GLM-OCR + PP-DocLayout with File Upload")

    complex_overrides = {
        "to_formats": ["json", "doctags"]
    }
    convert_file(SOURCE_IMG, "Complex Overrides with File Upload", custom_options=complex_overrides)