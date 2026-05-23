
"""
Document Extraction Engine — Streamlit UI
Run with: streamlit run app.py
"""
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import io
 
# ─── Config ──────────────────────────────────────────────────────────────────
 
API_URL = "http://localhost:8000"
 
DOCUMENT_TYPES = {
    "invoice": "🧾 Invoice",
    "resume": "📄 Resume / CV",
    "contract": "📝 Contract",
}
 
CONFIDENCE_CONFIG = {
    "high":      {"color": "#22c55e", "bg": "#dcfce7", "label": "HIGH"},
    "medium":    {"color": "#f59e0b", "bg": "#fef3c7", "label": "MEDIUM"},
    "low":       {"color": "#ef4444", "bg": "#fee2e2", "label": "LOW"},
    "corrected": {"color": "#6366f1", "bg": "#e0e7ff", "label": "CORRECTED"},
}
 
# ─── Page setup ──────────────────────────────────────────────────────────────
 
st.set_page_config(
    page_title="DocExtract Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ─── Custom CSS ──────────────────────────────────────────────────────────────
 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
 
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
 
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }
    .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }
    .main-header p { margin: 0.5rem 0 0; color: #94a3b8; font-size: 0.95rem; }
 
    .field-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .field-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .field-name {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 0.3rem;
    }
    .field-value {
        font-size: 0.95rem;
        color: #1e293b;
        font-weight: 500;
        font-family: 'JetBrains Mono', monospace;
        word-break: break-word;
    }
    .field-value.null-value { color: #94a3b8; font-style: italic; font-family: 'Inter', sans-serif; }
    .confidence-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        margin-left: 8px;
        vertical-align: middle;
    }
    .field-note {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 0.25rem;
        font-style: italic;
    }
 
    .summary-box {
        background: linear-gradient(135deg, #eff6ff, #f0fdf4);
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.25rem;
        border-radius: 0 12px 12px 0;
        margin-bottom: 1.5rem;
        font-size: 0.95rem;
        color: #1e293b;
    }
 
    .stat-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #0f172a; }
    .stat-label { font-size: 0.8rem; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
 
    .history-item {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.15s;
    }
    .history-item:hover { border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59,130,246,0.15); }
 
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .upload-zone {
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #f8fafc;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)
 
 
# ─── Helper functions ─────────────────────────────────────────────────────────
 
def confidence_badge_html(confidence: str) -> str:
    cfg = CONFIDENCE_CONFIG.get(confidence, CONFIDENCE_CONFIG["low"])
    return (
        f'<span class="confidence-badge" '
        f'style="background:{cfg["bg"]};color:{cfg["color"]};">'
        f'{cfg["label"]}</span>'
    )
 
 
def render_field_card(field: dict, editable: bool = False, edit_key: str = ""):
    name = field.get("field_name", "unknown").replace("_", " ").title()
    value = field.get("value")
    confidence = field.get("confidence", "low")
    note = field.get("note", "")
 
    badge = confidence_badge_html(confidence)
 
    if value is None:
        value_html = '<span class="field-value null-value">— not found —</span>'
    elif isinstance(value, (list, dict)):
        value_html = f'<span class="field-value">{json.dumps(value, indent=2)}</span>'
    else:
        value_html = f'<span class="field-value">{str(value)}</span>'
 
    note_html = f'<div class="field-note">ℹ️ {note}</div>' if note else ""
 
    st.markdown(f"""
    <div class="field-card">
        <div class="field-name">{name} {badge}</div>
        {value_html}
        {note_html}
    </div>
    """, unsafe_allow_html=True)
 
 
def format_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%b %d, %Y · %H:%M UTC")
    except Exception:
        return ts
 
 
def fields_to_dataframe(fields: list) -> pd.DataFrame:
    rows = []
    for f in fields:
        v = f.get("value")
        rows.append({
            "Field": f.get("field_name", "").replace("_", " ").title(),
            "Value": json.dumps(v) if isinstance(v, (list, dict)) else (str(v) if v is not None else ""),
            "Confidence": f.get("confidence", "").upper(),
            "Note": f.get("note", ""),
        })
    return pd.DataFrame(rows)
 
 
# ─── Sidebar ─────────────────────────────────────────────────────────────────
 
with st.sidebar:
    st.markdown("## 🔍 DocExtract")
    st.markdown("---")
 
    page = st.radio(
        "Navigate",
        ["📤 Extract Document", "📋 Past Extractions"],
        label_visibility="collapsed"
    )
 
    st.markdown("---")
    st.markdown("**Supported Documents**")
    for key, label in DOCUMENT_TYPES.items():
        st.markdown(f"- {label}")
 
    st.markdown("---")
    st.markdown("**Supported File Types**")
    st.markdown("- 📄 PDF\n- 📃 Plain Text (.txt)\n- 🖼️ Images (PNG/JPG)")
 
    # API status check
    st.markdown("---")
    try:
        r = requests.get(f"{API_URL}/", timeout=2)
        if r.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Error")
    except Exception:
        st.error("❌ API Offline\n\nStart backend:\n```\nuvicorn main:app --reload\n```")
 
 
# ─── Page: Extract Document ───────────────────────────────────────────────────
 
if "📤 Extract Document" in page:
 
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Document Extraction Engine</h1>
        <p>Upload any document → Get clean structured data powered by Gemini AI</p>
    </div>
    """, unsafe_allow_html=True)
 
    col1, col2 = st.columns([1, 1], gap="large")
 
    with col1:
        st.markdown("### 📁 Upload Document")
 
        doc_type_key = st.selectbox(
            "Document Type",
            options=list(DOCUMENT_TYPES.keys()),
            format_func=lambda x: DOCUMENT_TYPES[x],
        )
 
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "png", "jpg", "jpeg"],
            help="PDF, plain text, or image files supported",
        )
 
        if uploaded_file:
            st.markdown(f"""
            **Selected:** `{uploaded_file.name}`  
            **Size:** {uploaded_file.size / 1024:.1f} KB  
            **Type:** `{uploaded_file.type}`
            """)
 
        extract_btn = st.button(
            "🚀 Extract Data",
            disabled=uploaded_file is None,
            use_container_width=True,
            type="primary",
        )


    # ─── Extraction ──────────────────────────────────────────────────────────
 
if extract_btn and uploaded_file:
        with st.spinner("🧠 Gemini is reading your document..."):
            try:
                file_bytes = uploaded_file.read()
                files = {"file": (uploaded_file.name, file_bytes, uploaded_file.type)}
                data = {"document_type": doc_type_key}
 
                response = requests.post(
                    f"{API_URL}/extract",
                    files=files,
                    data=data,
                    timeout=60,
                )
 
                if response.status_code == 200:
                    result = response.json()
                    st.session_state["last_result"] = result
                    st.success(f"✅ Extraction complete! ID: `{result['id']}`")
                else:
                    err = response.json().get("detail", "Unknown error")
                    st.error(f"❌ Extraction failed: {err}")
 
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API. Is the backend running?\n\n`uvicorn main:app --reload`")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
 
    # ─── Display Result ───────────────────────────────────────────────────────
 
if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        extracted = result.get("extracted_data", {})
        fields = extracted.get("fields", [])
 
        st.markdown("---")
        st.markdown("## 📊 Extraction Results")
 
        # Meta info
        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
        with meta_col1:
            st.markdown(f"""<div class="stat-card"><div class="stat-number">{len(fields)}</div><div class="stat-label">Fields Found</div></div>""", unsafe_allow_html=True)
        with meta_col2:
            high_count = sum(1 for f in fields if f.get("confidence") == "high")
            st.markdown(f"""<div class="stat-card"><div class="stat-number" style="color:#22c55e">{high_count}</div><div class="stat-label">High Confidence</div></div>""", unsafe_allow_html=True)
        with meta_col3:
            null_count = sum(1 for f in fields if f.get("value") is None)
            st.markdown(f"""<div class="stat-card"><div class="stat-number" style="color:#94a3b8">{null_count}</div><div class="stat-label">Missing Fields</div></div>""", unsafe_allow_html=True)
        with meta_col4:
            overall = extracted.get("extraction_confidence", "?").upper()
            color_map = {"HIGH": "#22c55e", "MEDIUM": "#f59e0b", "LOW": "#ef4444"}
            color = color_map.get(overall, "#64748b")
            st.markdown(f"""<div class="stat-card"><div class="stat-number" style="color:{color}">{overall}</div><div class="stat-label">Overall Confidence</div></div>""", unsafe_allow_html=True)
 
        st.markdown("<br>", unsafe_allow_html=True)
 
        # Document summary
        if extracted.get("summary"):
            st.markdown(f"""<div class="summary-box">📝 {extracted['summary']}</div>""", unsafe_allow_html=True)
 
        # Tabs: Fields / JSON / Edit / Export
        tab1, tab2, tab3, tab4 = st.tabs(["🗂 Field View", "📦 Raw JSON", "✏️ Edit Fields", "📥 Export"])
 
        with tab1:
            if not fields:
                st.warning("No fields were extracted.")
            else:
                # Group by confidence
                cols = st.columns(2)
                for i, field in enumerate(fields):
                    with cols[i % 2]:
                        render_field_card(field)
 
        with tab2:
            st.code(json.dumps(extracted, indent=2), language="json")
 
        with tab3:
            st.markdown("**Correct any wrong values below, then save:**")
            corrections = {}
            for field in fields:
                fname = field.get("field_name", "")
                current_val = field.get("value")
                display_val = json.dumps(current_val) if isinstance(current_val, (list, dict)) else (str(current_val) if current_val is not None else "")
                new_val = st.text_input(
                    fname.replace("_", " ").title(),
                    value=display_val,
                    key=f"edit_{fname}"
                )
                if new_val != display_val and new_val.strip():
                    corrections[fname] = new_val
 
            if corrections and st.button("💾 Save Corrections", type="primary"):
                try:
                    r = requests.put(
                        f"{API_URL}/extractions/{result['id']}/correct",
                        json=corrections,
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.success("✅ Corrections saved!")
                    else:
                        st.error("Failed to save corrections.")
                except Exception as e:
                    st.error(f"Error: {e}")
 
        with tab4:
            df = fields_to_dataframe(fields)
 
            # CSV Export
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"extraction_{result['id'][:8]}.csv",
                mime="text/csv",
                use_container_width=True,
            )
 
            # Excel Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Extraction")
            st.download_button(
                label="📊 Download as Excel",
                data=buffer.getvalue(),
                file_name=f"extraction_{result['id'][:8]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
 
            # JSON Export
            st.download_button(
                label="📦 Download as JSON",
                data=json.dumps(extracted, indent=2),
                file_name=f"extraction_{result['id'][:8]}.json",
                mime="application/json",
                use_container_width=True,
            )
 
 
# ─── Page: Past Extractions ───────────────────────────────────────────────────
 
elif "📋 Past Extractions" in page:
 
    st.markdown("""
    <div class="main-header">
        <h1>📋 Extraction History</h1>
        <p>Browse and review all past document extractions</p>
    </div>
    """, unsafe_allow_html=True)
 
    try:
        response = requests.get(f"{API_URL}/extractions", timeout=5)
        if response.status_code != 200:
            st.error("Failed to load extractions.")
            st.stop()
 
        extractions = response.json()
 
        if not extractions:
            st.info("No extractions yet. Go to **Extract Document** to get started!")
            st.stop()
 
        st.markdown(f"**{len(extractions)} extractions found**")
        st.markdown("---")
 
        # Filter controls
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            type_filter = st.multiselect(
                "Filter by type",
                options=list(DOCUMENT_TYPES.keys()),
                format_func=lambda x: DOCUMENT_TYPES[x],
            )
        with f_col2:
            search = st.text_input("🔍 Search by filename", placeholder="e.g. invoice_jan...")
 
        # Apply filters
        filtered = extractions
        if type_filter:
            filtered = [e for e in filtered if e["document_type"] in type_filter]
        if search:
            filtered = [e for e in filtered if search.lower() in e["filename"].lower()]
 
        st.markdown(f"Showing **{len(filtered)}** results")
        st.markdown("")
 
        # List extractions
        for extraction in filtered:
            type_label = DOCUMENT_TYPES.get(extraction["document_type"], extraction["document_type"])
            ts = format_timestamp(extraction.get("timestamp", ""))
            field_count = extraction.get("field_count", "?")
 
            with st.expander(f"{type_label} · **{extraction['filename']}** · {ts}"):
                # Fetch full details
                detail_resp = requests.get(f"{API_URL}/extractions/{extraction['id']}", timeout=5)
                if detail_resp.status_code != 200:
                    st.error("Could not load details.")
                    continue
 
                detail = detail_resp.json()
                fields = detail.get("extracted_data", {}).get("fields", [])
                summary = detail.get("extracted_data", {}).get("summary", "")
 
                st.markdown(f"**ID:** `{detail['id']}`")
                if summary:
                    st.markdown(f"""<div class="summary-box">📝 {summary}</div>""", unsafe_allow_html=True)
 
                if fields:
                    cols = st.columns(2)
                    for i, field in enumerate(fields):
                        with cols[i % 2]:
                            render_field_card(field)
 
                    # Export from history
                    df = fields_to_dataframe(fields)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        f"📥 Export CSV",
                        data=csv,
                        file_name=f"extraction_{detail['id'][:8]}.csv",
                        mime="text/csv",
                        key=f"csv_{detail['id']}"
                    )
 
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure the backend is running.")
    except Exception as e:
        st.error(f"Error loading history: {e}")