from pydantic import BaseModel, field_serializer, Field
from datetime import datetime



class ReturnFile(BaseModel):
    id: int = Field(..., example=1, description="File identification number")
    filename: str = Field(..., example="name", description="File name provided by the user")
    size_bytes: int = Field(..., example=4005, description="File size in bytes")
    uploaded_at: datetime = Field(..., example="2025-09-03T12:34:56Z", description="Time at which the file was transferred")

    @field_serializer('filename')
    def clean_filename(self, v: str) -> str:
        parts = v.split('_')
        return '_'.join(parts[2:]) if len(parts) > 2 else v

    class Config:
        from_attributes = True