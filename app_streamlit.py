"""
Mistral OCR App - Document Classification and Splitting
Supports both local development and Streamlit Cloud deployment
"""
import os
import json
import base64
import tempfile
import zipfile
import streamlit as st
from mistralai import Mistral
from dotenv import find_dotenv, load_dotenv
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk
from mistralai.models import OCRResponse
from enum import Enum
from pydantic import BaseModel
import pycountry
from langchain_google_vertexai import ChatVertexAI
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

# Load environment variables (for local development)
load_dotenv(find_dotenv())

# Handle secrets for both local and Streamlit Cloud deployment
def get_secrets():
    """Get API keys and credentials from either Streamlit secrets or .env file"""
    secrets = {}
    
    # Check if running on Streamlit Cloud
    if hasattr(st, 'secrets') and len(st.secrets) > 0:
        # Running on Streamlit Cloud
        secrets['mistral_api_key'] = st.secrets.get("MISTRAL_API_KEY")
        
        # Handle Google Cloud service account (for Vertex AI)
        if "gcp_service_account" in st.secrets:
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            # Create temporary credentials file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(service_account_info, f)
                secrets['google_creds_path'] = f.name
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
        
        # Or use Google AI Studio API key (simpler alternative)
        if "GOOGLE_API_KEY" in st.secrets:
            secrets['google_api_key'] = st.secrets["GOOGLE_API_KEY"]
            os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    else:
        # Running locally with .env
        secrets['mistral_api_key'] = os.environ.get("MISTRAL_API_KEY")
        secrets['google_api_key'] = os.environ.get("GOOGLE_API_KEY")
        secrets['google_creds_path'] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    return secrets

# Get secrets
app_secrets = get_secrets()
api_key = app_secrets['mistral_api_key']

if not api_key:
    st.error("⚠️ MISTRAL_API_KEY not found. Please configure secrets in Streamlit Cloud or add to .env file locally.")
    st.stop()

client = Mistral(api_key=api_key)

# Initialize LLM (Gemini)
try:
    llm = ChatVertexAI(
        model="gemini-2.5-pro",  # Use a valid, stable model
        temperature=0.3,
    )
except Exception as e:
    st.error(f"⚠️ Failed to initialize Gemini model: {e}")
    st.info("Please ensure GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_API_KEY is configured correctly.")
    st.stop()

# Define Language Enum
languages = {lang.alpha_2: lang.name for lang in pycountry.languages if hasattr(lang, 'alpha_2')}


class LanguageMeta(Enum.__class__):
    def __new__(metacls, cls, bases, classdict):
        for code, name in languages.items():
            classdict[name.upper().replace(' ', '_')] = name
        return super().__new__(metacls, cls, bases, classdict)


class Language(Enum, metaclass=LanguageMeta):
    pass


class StructuredOCR(BaseModel):
    file_name: str
    topics: list[str]
    languages: list[Language]
    ocr_contents: dict

pageWiseData = {}

def categorize_documents():
    print("Classifying document pages...")
    prompt = f"""
    You are an expert document classification AI.
    Task:
    Classify each page into one of the following categories:

    ["tenth-marksheet","twelfth-marksheet","passport","passport-receipt",
    "english-test-toefl","english-test-ielts","english-test-pte","english-test-duolingo",
    "proficiency-test-gre","proficiency-test-gmat",
    "under-graduate-degree-provisional-certificate","undergraduate-degree-original-certificate",
    "under-graduate-marksheets-semester-wise-or-year-wise",
    "post-graduate-degree-provisional-certificate","postgraduate-degree-original-certificate",
    "post-graduate-marksheets-semester-wise-or-year-wise",
    "resume","work-experience-letter","aadhaar-card",
    "lor-academic","lor-professional","statement-of-purpose","letter-of-recommendation","unknown"]

    Rules:
    1. Only use one category per page.
    2. If a page doesn't match any category, classify it as "unknown".
    3. Ignore images, tables, or decorative content; classify based on textual content.
    4. Output **strictly in JSON format**, where keys are category names and values are arrays of page numbers (integers).

    Example Output:
    {{
    "tenth-marksheet": [],
    "twelfth-marksheet": [1],
    "passport": [2,3],
    "statement-of-purpose": [10,11],
    "resume": [7],
    "unknown": [9,14]
    }}

    Here is the page data to classify:
    {pageWiseData}
    """
    response = llm.invoke(prompt)
    print("Gemini Response:", response)

    try:
        # Parse Gemini JSON response
        response_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:].strip()
        
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()
        
        categories = json.loads(response_text)
        print("Document Categories:", categories)
        return categories
    except Exception as e:
        print("Failed to parse Gemini response:", e)
        print("Raw response:", response.content)
        st.error(f"Failed to parse classification results: {e}")
        return None

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})")
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    markdowns: list[str] = []
    
    for page in ocr_response.pages:
        print("page", page)
        image_data = {img.id: img.image_base64 for img in page.images}
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))
        pageWiseData[page.index] = {
            "markdown": page.markdown
        }
    return "\n\n".join(markdowns)

def process_pdf(pdf_bytes, file_name):
    """Process a PDF using OCR."""
    uploaded_file = client.files.upload(
        file={"file_name": file_name, "content": pdf_bytes},
        purpose="ocr",
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True,
    )

    if isinstance(pdf_response, dict):
        pdf_response = OCRResponse(**pdf_response)

    return pdf_response


def splitPdfBasedOnCategories(documentsData, file_bytes):
    """Split a PDF into multiple PDFs based on document categories."""
    print("Splitting PDF based on categories...")
    
    pdf_reader = PdfReader(BytesIO(file_bytes))
    total_pages = len(pdf_reader.pages)
    print(f"Total pages in PDF: {total_pages}")
    
    split_pdfs = {}
    
    for category, pages in documentsData.items():
        if len(pages) > 0:
            print(f"Creating PDF for category: {category}, Pages: {pages}")
            
            pdf_writer = PdfWriter()
            
            for page_num in pages:
                if page_num < total_pages:
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                else:
                    print(f"Warning: Page {page_num} does not exist in the PDF (total pages: {total_pages})")
            
            output_buffer = BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            split_pdfs[category] = output_buffer.getvalue()
            print(f"✅ Created {category}.pdf with {len(pages)} pages")
    
    return split_pdfs

def create_zip_from_pdfs(split_pdfs: dict) -> bytes:
    """
    Create a ZIP file containing all categorized PDFs.
    
    Args:
        split_pdfs: Dictionary with category names as keys and PDF bytes as values
    
    Returns:
        ZIP file as bytes
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for category, pdf_bytes in split_pdfs.items():
            # Add each PDF to the ZIP with a clean filename
            filename = f"{category}.pdf"
            zip_file.writestr(filename, pdf_bytes)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# Streamlit UI
st.set_page_config(
    page_title="Mistral OCR - Document Classifier",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Multi Page Document Classifier")
st.markdown("Upload a PDF to automatically classify and split documents by category.")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], help="Upload a multi-page PDF document")

if uploaded_file:
    file_type = uploaded_file.type
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    if st.button("🚀 Process Document", type="primary"):
        with st.spinner(f"Processing {file_name}..."):
            if "pdf" in file_type:
                try:
                    st.info("🔍 Step 1: Extracting text from PDF using OCR...")
                    pdf_response = process_pdf(file_bytes, file_name)
                    
                    st.success(f"✅ OCR completed! Found {len(pdf_response.pages)} pages.")
                    
                    st.info("📝 Step 2: Analyzing document content...")
                    combined_markdown = get_combined_markdown(pdf_response)
                    
                    with st.expander("📄 View OCR Content"):
                        st.markdown(combined_markdown)
                    
                    st.info("🏷️ Step 3: Categorizing pages...")
                    documentsData = categorize_documents()
                    
                    if documentsData:
                        st.success("✅ Categorization complete!")
                        
                        st.subheader("📊 Document Classification Summary")
                        non_empty_categories = {cat: pages for cat, pages in documentsData.items() if len(pages) > 0}
                        
                        if non_empty_categories:
                            for category, pages in non_empty_categories.items():
                                st.write(f"**{category.replace('-', ' ').title()}**: Pages {pages}")
                        
                        st.info("✂️ Step 4: Splitting PDF by categories...")
                        split_pdfs = splitPdfBasedOnCategories(documentsData, file_bytes)
                        
                        if split_pdfs:
                            st.success(f"✅ Created {len(split_pdfs)} separate PDF files!")
                            
                            st.subheader("📥 Download Split PDFs")
                            
                            # Add bulk download button at the top
                            zip_bytes = create_zip_from_pdfs(split_pdfs)
                            st.download_button(
                                label=f"📦 Download All PDFs as ZIP ({len(split_pdfs)} files)",
                                data=zip_bytes,
                                file_name=f"{file_name.rsplit('.', 1)[0]}_categorized.zip",
                                mime="application/zip",
                                type="primary",
                                use_container_width=True
                            )
                            
                            st.markdown("---")
                            st.markdown("**Or download individual PDFs:**")
                            
                            cols = st.columns(2)
                            col_idx = 0
                            
                            
                            for category, pdf_bytes in split_pdfs.items():
                                with cols[col_idx % 2]:
                                    st.download_button(
                                        label=f"📄 {category.replace('-', ' ').title()} ({len(documentsData[category])} pages)",
                                        data=pdf_bytes,
                                        file_name=f"{category}.pdf",
                                        mime="application/pdf",
                                        key=f"download_{category}"
                                    )
                                col_idx += 1
                            
                        else:
                            st.warning("No PDFs were created. All categories might be empty.")
                    else:
                        st.error("Failed to categorize documents. Please try again.")
                        
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    st.exception(e)
else:
    st.info("👆 Upload a PDF document to get started")

st.markdown("---")
st.markdown("Built with Mistral OCR & Gemini AI | Deployed on Streamlit Cloud")
