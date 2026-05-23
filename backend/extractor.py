
"""
LLM Extraction Engine
Uses Gemini API to extract structured data from raw document text.
 
Prompt Design Philosophy:
- System prompt defines the role: strict data extractor, never hallucinate
- Each document type has its own schema definition embedded in the prompt
- Confidence scoring: "high" if value is explicit/clear, "medium" if inferred, "low" if ambiguous
- Missing fields: return null with a descriptive note
- Output is always valid JSON matching our schema
"""
import json
import os
import re
import google.generativeai as genai
import time

 
# ─── Schema definitions ────────────────────────────────────────────────────────
 
SCHEMAS = {
    "invoice": {
        "description": "A financial invoice document from a vendor",
        "fields": [
            {"name": "vendor_name", "description": "Name of the company or person issuing the invoice", "required": True},
            {"name": "vendor_address", "description": "Full address of the vendor", "required": False},
            {"name": "invoice_number", "description": "Unique invoice identifier/number", "required": True},
            {"name": "invoice_date", "description": "Date the invoice was issued (ISO format if possible)", "required": True},
            {"name": "due_date", "description": "Payment due date", "required": False},
            {"name": "bill_to_name", "description": "Name of client being billed", "required": True},
            {"name": "bill_to_address", "description": "Address of client being billed", "required": False},
            {"name": "line_items", "description": "List of items/services: [{description, quantity, unit_price, total}]", "required": True},
            {"name": "subtotal", "description": "Sum before taxes/discounts", "required": False},
            {"name": "tax_amount", "description": "Tax charged", "required": False},
            {"name": "discount", "description": "Any discount applied", "required": False},
            {"name": "total_amount", "description": "Final total amount due (include currency symbol)", "required": True},
            {"name": "currency", "description": "Currency code e.g. USD, EUR, INR", "required": False},
            {"name": "payment_terms", "description": "Payment conditions e.g. Net 30", "required": False},
            {"name": "notes", "description": "Any additional notes or remarks", "required": False},
        ]
    },
    "resume": {
        "description": "A professional resume or CV document",
        "fields": [
            {"name": "full_name", "description": "Candidate's full name", "required": True},
            {"name": "email", "description": "Email address", "required": True},
            {"name": "phone", "description": "Phone number", "required": False},
            {"name": "location", "description": "City, state, country", "required": False},
            {"name": "linkedin_url", "description": "LinkedIn profile URL", "required": False},
            {"name": "summary", "description": "Professional summary or objective statement", "required": False},
            {"name": "skills", "description": "List of technical and soft skills", "required": True},
            {"name": "experience", "description": "Work history: [{company, title, duration, responsibilities}]", "required": True},
            {"name": "education", "description": "Education history: [{institution, degree, field, year}]", "required": True},
            {"name": "certifications", "description": "List of certifications or licenses", "required": False},
            {"name": "languages", "description": "Languages spoken with proficiency level", "required": False},
            {"name": "projects", "description": "Notable projects: [{name, description, technologies}]", "required": False},
        ]
    },
    "contract": {
        "description": "A legal contract or agreement document",
        "fields": [
            {"name": "contract_title", "description": "Title or type of contract", "required": True},
            {"name": "party_one", "description": "First party name and role", "required": True},
            {"name": "party_two", "description": "Second party name and role", "required": True},
            {"name": "effective_date", "description": "Date the contract becomes effective", "required": True},
            {"name": "expiry_date", "description": "Contract end date if applicable", "required": False},
            {"name": "contract_value", "description": "Monetary value of the contract if stated", "required": False},
            {"name": "jurisdiction", "description": "Governing law / jurisdiction", "required": False},
            {"name": "key_obligations", "description": "Main obligations of each party", "required": True},
            {"name": "termination_clause", "description": "Conditions for contract termination", "required": False},
            {"name": "payment_terms", "description": "Payment schedule and terms", "required": False},
            {"name": "confidentiality", "description": "Whether there is a confidentiality/NDA clause", "required": False},
            {"name": "signatures", "description": "Signatories listed: [{name, title, date}]", "required": False},
        ]
    }
}
 
# ─── System prompt ──────────────────────────────────────────────────────────────
 
SYSTEM_PROMPT = """You are a precise document data extraction engine. Your job is to extract structured information from document text.
 
STRICT RULES — follow these exactly:
1. NEVER hallucinate or invent values. If a field is not present in the document, return null.
2. NEVER guess. Only extract values that are clearly present in the text.
3. For each field, assign a confidence score:
   - "high": value is explicitly stated and unambiguous
   - "medium": value is implied or needs minor interpretation
   - "low": value is partially present, ambiguous, or inferred from context
4. If a required field is missing, include a note explaining why it's null.
5. Return ONLY valid JSON — no markdown, no explanation, no preamble.
6. For list fields (line_items, experience, etc.), return a proper JSON array.
 
OUTPUT FORMAT (return exactly this structure):
{
  "document_type": "<type>",
  "extraction_confidence": "high|medium|low",
  "fields": [
    {
      "field_name": "<name>",
      "value": <extracted value or null>,
      "confidence": "high|medium|low",
      "note": "<optional explanation if null or uncertain>"
    }
  ],
  "summary": "<one sentence summary of the document>"
}"""
 
 
# ─── Main extraction function ───────────────────────────────────────────────────
 
def extract_document(raw_text: str, document_type: str) -> dict:
    """
    Send raw text + schema to Gemini, get back structured JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
 
    genai.configure(api_key=api_key)
 
    schema = SCHEMAS.get(document_type)
    if not schema:
        raise ValueError(f"Unknown document type: {document_type}")
 
    # Build the extraction prompt
    fields_spec = "\n".join([
        f"  - {f['name']} {'[REQUIRED]' if f['required'] else '[optional]'}: {f['description']}"
        for f in schema["fields"]
    ])
 
    user_prompt = f"""Extract data from this {document_type.upper()} document.
 
DOCUMENT TYPE: {schema['description']}
 
FIELDS TO EXTRACT:
{fields_spec}
 
DOCUMENT TEXT:
---
{raw_text[:8000]}
---
 
Return the structured JSON extraction following the format defined in your instructions. Remember: null for missing fields, never hallucinate."""
 
    model = genai.GenerativeModel(
        model_name="models/gemini-3.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
 
    response = model.generate_content(user_prompt)

    raw_response = response.text.strip()
 
    # Clean up response — remove markdown code fences if present
    raw_response = re.sub(r"^```json\s*", "", raw_response)
    raw_response = re.sub(r"^```\s*", "", raw_response)
    raw_response = re.sub(r"\s*```$", "", raw_response).strip()
 
    # Parse JSON
    try:
        extracted = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}\nRaw response: {raw_response[:500]}")
 
    # Validate structure
    _validate_extraction_structure(extracted)
 
    return extracted
 
 
def _validate_extraction_structure(data: dict):
    """Basic validation of extraction output structure."""
    required_keys = ["document_type", "fields", "extraction_confidence"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Extraction missing required key: '{key}'")
 
    if not isinstance(data["fields"], list):
        raise ValueError("'fields' must be a list")
 
    for field in data["fields"]:
        if "field_name" not in field:
            raise ValueError(f"Field missing 'field_name': {field}")
        if "confidence" not in field:
            field["confidence"] = "low"  # default
        if field["confidence"] not in ["high", "medium", "low", "corrected"]:
            field["confidence"] = "low"