from pydantic import BaseModel, Field

class PythonRCode(BaseModel):
    cat: str = Field(..., description="Programming language of the cat")
    dog: str = Field(..., description="Programming language of the dog")
    dog_code_number: int = Field(..., description="Dog number of code scripts")


print(PythonRCode.model_json_schema())