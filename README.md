# Document Extraction Engine

An AI-powered document extraction engine that accepts uploaded files (PDFs, text files, and images) and returns clean, structured JSON — powered by Google Gemini AI, FastAPI, and Streamlit.

# Project Structure
doc-extractor/
├── backend/
│   ├── main.py          → FastAPI app (all API routes)
│   ├── extractor.py     → Gemini AI + prompt logic + schemas
│   ├── file_utils.py    → PDF / text / image text extraction
│   ├── models.py        → Pydantic data models
│   ├── storage.py       → JSON file-based storage
│   ├── requirements.txt → Backend dependencies
│   └── .env             → Your Gemini API key (never commit this)
│
├── frontend/
    ├── app.py           → Streamlit UI
    └── requirements.txt → Frontend dependencies


# Setup Steps
Step 1 — Get a Gemini API Key

Go to https://aistudio.google.com/app/apikey
Click "Create API key in new project"
Copy the key (starts with AIza...)


Step 2 — Setup Backend
Open a terminal and run:
bash# Go to backend folder
cd doc-extractor/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key to .env file
# Open .env and set:
# GEMINI_API_KEY=AIzaYourKeyHere

# Start backend server
uvicorn main:app --reload --port 8000
Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

Step 3 — Setup Frontend
Open a second terminal and run:
bash# Go to frontend folder
cd doc-extractor/frontend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Streamlit
streamlit run app.py
Frontend runs at: http://localhost:8501

Step 4 — Test the App

Open http://localhost:8501
Select document type (Invoice / Resume / Contract)
Upload any file from sample_docs/
Click Extract Data
View results with confidence scores


# Prompt Design Explanation
The extraction engine uses a two-part prompt strategy:
Part 1 — System Prompt (Rules)
The system prompt is sent once and defines strict rules for the AI:
You are a precise document data extraction engine.

STRICT RULES:
1. NEVER hallucinate or invent values
2. If a field is not present, return null
3. Assign confidence scores:
   - "high"   → value is explicitly and clearly stated
   - "medium" → value is implied or needs minor interpretation
   - "low"    → value is ambiguous or partially found
4. Return ONLY valid JSON — no markdown, no explanation
5. Missing required fields must include a note explaining why
Part 2 — User Prompt (Task)
The user prompt is dynamically built for each document type. It includes:

The document type and description
A list of every field to extract with REQUIRED / optional labels
The actual document text (up to 8000 characters)
The exact JSON format expected in the response

Why this approach works

Separating rules (system) from task (user) gives the model clear boundaries
Listing fields explicitly tells the model exactly what to look for
Marking fields as REQUIRED forces the model to always return them (even as null)
Asking for confidence scores makes the model reason about certainty
Requesting only JSON prevents any extra text that would break parsing


# Schema Definitions
Invoice Schema
FieldRequiredDescriptionvendor_nameYESName of company issuing the invoicevendor_addressnoFull address of vendorinvoice_numberYESUnique invoice IDinvoice_dateYESDate invoice was issueddue_datenoPayment deadlinebill_to_nameYESClient being billedbill_to_addressnoClient addressline_itemsYESList of {description, quantity, unit_price, total}subtotalnoAmount before taxtax_amountnoTax chargeddiscountnoAny discount appliedtotal_amountYESFinal total duecurrencynoCurrency code (USD, INR, EUR)payment_termsnoe.g. Net 30notesnoAdditional remarks

Resume Schema
FieldRequiredDescriptionfull_nameYESCandidate full nameemailYESEmail addressphonenoPhone numberlocationnoCity, state, countrylinkedin_urlnoLinkedIn profile URLsummarynoProfessional summaryskillsYESList of skillsexperienceYESList of {company, title, duration, responsibilities}educationYESList of {institution, degree, field, year}certificationsnoList of certificationslanguagesnoLanguages with proficiencyprojectsnoList of {name, description, technologies}

Contract Schema
FieldRequiredDescriptioncontract_titleYESType/title of contractparty_oneYESFirst party name and roleparty_twoYESSecond party name and roleeffective_dateYESContract start dateexpiry_datenoContract end datecontract_valuenoMonetary value if statedjurisdictionnoGoverning law/locationkey_obligationsYESMain duties of each partytermination_clausenoConditions to end contractpayment_termsnoPayment scheduleconfidentialitynoWhether NDA clause existssignaturesnoList of {name, title, date}

# How Extraction Failures Are Handled
The engine handles every type of failure gracefully:
1. Unsupported File Type

What happens: User uploads a .docx or .mp4 file
How handled: Returns HTTP 400 immediately with message:
"Unsupported file type '.docx'. Supported: [.pdf, .txt, .png, .jpg, .jpeg]"

2. Empty or Unreadable File

What happens: File uploads but contains no text
How handled: Returns HTTP 422 with message:
"Could not extract meaningful text from the document"

3. Scanned / Image-based PDF

What happens: PDF has no selectable text (pure scan)
How handled: pdfplumber returns empty → PyMuPDF tries as fallback → if still empty, returns helpful error suggesting user upload as image file instead

4. Gemini Returns Invalid JSON

What happens: AI response is malformed or contains extra text
How handled: Code strips markdown fences (```json) before parsing. If JSON still fails, returns HTTP 500 with the raw response snippet for debugging

5. Required Field Missing in Document

What happens: e.g. invoice has no vendor name
How handled: Field is returned as:

json  {
    "field_name": "vendor_name",
    "value": null,
    "confidence": "low",
    "note": "Vendor name not found in document"
  }
Never guessed. Never hallucinated.
6. Gemini API Rate Limit (429 Error)

What happens: Free tier limit exceeded (20 requests/day)
How handled: Auto-retry with 15 second wait. If still failing, returns clear error message with instructions to wait or create new API key

7. Gemini API Key Missing

What happens: .env file not configured
How handled: Returns HTTP 500 with message: "GEMINI_API_KEY environment variable is not set"

8. API Connection Timeout

What happens: Gemini takes too long to respond
How handled: Frontend timeout set to 120 seconds. Backend retries once before failing.


# Confidence Scoring
ScoreColorMeaningExampleHIGH🟢 GreenValue explicitly stated"Invoice No: INV-001"MEDIUM🟡 YellowRequires minor interpretationDate format conversionLOW🔴 RedAmbiguous or partially foundUnclear handwritingCORRECTED🟣 PurpleUser manually correctedAny user edit

# API Endpoints
MethodEndpointDescriptionPOST/extractUpload file, get structured JSONGET/extractionsList all past extractionsGET/extractions/{id}Get full extraction by IDPUT/extractions/{id}/correctSave user corrections

# How to Improve Accuracy
Current Limitations

Scanned PDFs — Image-based PDFs return no text. Fix: run Gemini Vision on each page
Complex tables — Merged cells lose alignment. Fix: use pdfplumber table extraction API
Handwritten documents — Not well supported. Fix: specialized OCR models
Very long documents — Truncated at 8000 characters. Fix: chunking + multi-pass extraction
Non-standard layouts — Unusual invoice formats may miss fields. Fix: few-shot examples in prompt

# Production Improvements

Add 2-3 few-shot examples in the prompt for better accuracy
Two-pass extraction: first extract, second validate and fix
Auto-detect document type from content
Use regex to verify extracted phone numbers, emails, dates, totals
Replace JSON file storage with PostgreSQL for scale
Add Celery queue for batch document processing


# Tech Stack
Backend APIPython 3.10+ + -> FastAPI
AIModel -> Google Gemini 2.5 Flash
PDF Parsing -> pdfplumber + PyMuPDF
Image OCR -> Gemini Vision API
Validation -> Pydantic v2
Storage -> JSON files
Frontend -> Streamlit
Exportpandas + openpyxl
