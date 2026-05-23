
"""
Document Extraction Engine - FastAPI Backend
"""
from dotenv import load_dotenv
load_dotenv()

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
 
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
 
from extractor import extract_document
from models import ExtractionRecord, ExtractionResponse
from storage import save_extraction, get_all_extractions, get_extraction_by_id
from file_utils import extract_text_from_file
 
app = FastAPI(title="Document Extraction Engine", version="1.0.0")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
SUPPORTED_TYPES = ["invoice", "resume", "contract"]
SUPPORTED_EXTENSIONS = [".pdf", ".txt", ".png", ".jpg", ".jpeg"]
 
 
@app.get("/")
def root():
    return {"message": "Document Extraction Engine API", "version": "1.0.0"}
 
 
@app.post("/extract", response_model=ExtractionResponse)
async def extract(
    file: UploadFile = File(...),
    document_type: str = Form(...),
):
    # Validate document type
    if document_type.lower() not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type '{document_type}'. Choose from: {SUPPORTED_TYPES}"
        )
 
    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported: {SUPPORTED_EXTENSIONS}"
        )
 
    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
 
    # Extract raw text from file
    try:
        raw_text = extract_text_from_file(file_bytes, suffix, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract text from file: {str(e)}")
 
    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Could not extract meaningful text from the document.")
 
    # Run LLM extraction
    try:
        extracted_data = extract_document(raw_text, document_type.lower())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
 
    # Build and save record
    record = ExtractionRecord(
        id=str(uuid.uuid4()),
        filename=file.filename,
        document_type=document_type.lower(),
        timestamp=datetime.utcnow().isoformat(),
        extracted_data=extracted_data,
        raw_text_length=len(raw_text),
    )
    save_extraction(record)
 
    return ExtractionResponse(
        id=record.id,
        filename=record.filename,
        document_type=record.document_type,
        timestamp=record.timestamp,
        extracted_data=extracted_data,
    )
 
 
@app.get("/extractions")
def list_extractions():
    records = get_all_extractions()
    return [
        {
            "id": r["id"],
            "filename": r["filename"],
            "document_type": r["document_type"],
            "timestamp": r["timestamp"],
            "field_count": len(r.get("extracted_data", {}).get("fields", [])),
        }
        for r in records
    ]
 
 
@app.get("/extractions/{extraction_id}")
def get_extraction(extraction_id: str):
    record = get_extraction_by_id(extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")
    return record
 
 
@app.put("/extractions/{extraction_id}/correct")
def correct_extraction(extraction_id: str, corrections: dict):
    """Allow user to save corrected field values."""
    record = get_extraction_by_id(extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")
 
    # Apply corrections to fields
    fields = record.get("extracted_data", {}).get("fields", [])
    corrected_fields = []
    for field in fields:
        field_name = field.get("field_name")
        if field_name in corrections:
            field["value"] = corrections[field_name]
            field["confidence"] = "corrected"
            field["corrected"] = True
        corrected_fields.append(field)
 
    record["extracted_data"]["fields"] = corrected_fields
    record["corrected_at"] = datetime.utcnow().isoformat()
    save_extraction(ExtractionRecord(**{k: v for k, v in record.items() if k != "corrected_at"}), overwrite=True)
 
    return {"message": "Corrections saved.", "id": extraction_id}