"""
Pydantic models for schema validation
"""
from typing import Any, Optional
from pydantic import BaseModel
 
 
class ExtractionRecord(BaseModel):
    id: str
    filename: str
    document_type: str
    timestamp: str
    extracted_data: dict
    raw_text_length: int = 0
 
 
class ExtractionResponse(BaseModel):
    id: str
    filename: str
    document_type: str
    timestamp: str
    extracted_data: dict
 