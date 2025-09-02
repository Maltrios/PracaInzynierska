from pydantic import BaseModel, field_serializer
from datetime import datetime

class ReturnFile(BaseModel):
    id: int
    filename: str
    size_bytes: int
    uploaded_at: datetime

    @field_serializer('filename')
    def clean_filename(self, v: str) -> str:
        parts = v.split('_')
        return '_'.join(parts[2:]) if len(parts) > 2 else v

    class Config:
        from_attributes = True