import os
import json
import base64
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
# Load environment variables
load_dotenv(find_dotenv())
llm = ChatVertexAI(
    model="gemini-2.5-pro",
    temperature=0.3,
    # api_key=os.environ.get("GOOGLE_API_KEY")
)


api_key = os.environ.get("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

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
    print("Classifying document pages...");
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
    2. If a page doesn’t match any category, classify it as "unknown".
    3. Ignore images, tables, or decorative content; classify based on textual content.
    4. Output **strictly in JSON format**, where keys are category names and values are arrays of page numbers (integers).

    Example Output:
    {{
    "tenth-marksheet": ,
    "twelfth-marksheet": [1],
    "passport": [2,3],
    "statement-of-purpose": [10,11],
    "resume": [7],
    "unknown": [9,14]
    }}

    Here is the page data to classify:
    {pageWiseData}
    """
    response=llm.invoke(prompt);
    print("Gemini Response:", response);

    try:
        # Parse Gemini JSON response
        response_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:].strip()  # Remove ```json and strip whitespace
        elif response_text.startswith("```"):
            response_text = response_text[3:].strip()  # Remove ``` and strip whitespace
        
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()  # Remove trailing ``` and strip whitespace
        
        categories = json.loads(response_text)
        print("Document Categories:", categories)
        return categories
    except Exception as e:
        print("Failed to parse Gemini response:", e)
        print("Raw response:", response.content)
        return

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
            "markdown":page.markdown
        }
    return "\n\n".join(markdowns)

def process_pdf(pdf_bytes, file_name):
    """Process a PDF using OCR."""
    uploaded_file = client.files.upload(
        file={"file_name": file_name, "content": pdf_bytes},
        purpose = "ocr",
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True,
    )

    # Ensure pdf_response is properly converted to OCRResponse model
    if isinstance(pdf_response, dict):  # If response is a dictionary, convert it
        pdf_response = OCRResponse(**pdf_response)

    return pdf_response


# def process_image(image_bytes, file_name):
    """Process an image using OCR."""
    encoded_image = base64.b64encode(image_bytes).decode()
    base64_data_url = f"data:image/jpeg;base64,{encoded_image}"
    image_response = client.ocr.process(
        document=ImageURLChunk(image_url=base64_data_url), model="mistral-ocr-latest"
    )
    image_ocr_markdown = image_response.pages[0].markdown

    chat_response = client.chat.parse(
        model="pixtral-12b-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    ImageURLChunk(image_url=base64_data_url),
                    TextChunk(
                        text=(
                            "This is the image's OCR in markdown:\n"
                            f"<BEGIN_IMAGE_OCR>\n{image_ocr_markdown}\n<END_IMAGE_OCR>.\n"
                            "Convert this into a structured JSON response with the OCR contents in a dictionary."
                        )
                    ),
                ],
            },
        ],
        response_format=StructuredOCR,
        temperature=0,
    )
    return json.loads(chat_response.choices[0].message.parsed.model_dump_json())

def splitPdfBasedOnCategories(documentsData, file_bytes):
    """
    Split a PDF into multiple PDFs based on document categories.
    
    Args:
        documentsData: Dictionary with category names as keys and page numbers as values
        file_bytes: The original PDF file as bytes
    
    Returns:
        Dictionary with category names as keys and file bytes as values
    """
   
    from io import BytesIO
    
    print("Splitting PDF based on categories...")
    
    # Load the PDF from bytes
    pdf_reader = PdfReader(BytesIO(file_bytes))
    total_pages = len(pdf_reader.pages)
    print(f"Total pages in PDF: {total_pages}")
    
    split_pdfs = {}
    
    for category, pages in documentsData.items():
        if len(pages) > 0:
            print(f"Creating PDF for category: {category}, Pages: {pages}")
            
            # Create a new PDF writer for this category
            pdf_writer = PdfWriter()
            
            # Add each page to the new PDF
            for page_num in pages:
                if page_num < total_pages:  # Safety check
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                else:
                    print(f"Warning: Page {page_num} does not exist in the PDF (total pages: {total_pages})")
            
            # Write the PDF to bytes
            output_buffer = BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            # Store the PDF bytes
            split_pdfs[category] = output_buffer.getvalue()
            print(f"✅ Created {category}.pdf with {len(pages)} pages")
    
    return split_pdfs

# Streamlit UI
st.title("Mistral OCR")

uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    file_type = uploaded_file.type
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    if st.button("Submit"):
        with st.spinner(f"Processing file: {file_name}..."):
            if "pdf" in file_type:
                # Process PDF
                st.info("🔍 Step 1: Extracting text from PDF using OCR...")
                pdf_response = process_pdf(file_bytes, file_name)
                
                st.success(f"✅ OCR completed! Found {len(pdf_response.pages)} pages.")
                
                # Get markdown content
                st.info("📝 Step 2: Analyzing document content...")
                combined_markdown = get_combined_markdown(pdf_response)
                
                # Show OCR preview in expander
                with st.expander("📄 View OCR Content"):
                    st.markdown(combined_markdown)
                
                # Categorize documents
                st.info("🏷️ Step 3: Categorizing pages...")
                documentsData = categorize_documents()
                
                if documentsData:
                    # Display categorization results
                    st.success("✅ Categorization complete!")
                    
                    # Show summary
                    st.subheader("📊 Document Classification Summary")
                    non_empty_categories = {cat: pages for cat, pages in documentsData.items() if len(pages) > 0}
                    
                    if non_empty_categories:
                        for category, pages in non_empty_categories.items():
                            st.write(f"**{category.replace('-', ' ').title()}**: Pages {pages}")
                    
                    # Split PDFs
                    st.info("✂️ Step 4: Splitting PDF by categories...")
                    split_pdfs = splitPdfBasedOnCategories(documentsData, file_bytes)
                    
                    if split_pdfs:
                        st.success(f"✅ Created {len(split_pdfs)} separate PDF files!")
                        
                        # Display download buttons
                        st.subheader("📥 Download Split PDFs")
                        
                        # Create columns for better layout
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
                    
            # else:
            #     st.info("🔍 Processing image using OCR...")
            #     result = process_image(file_bytes, file_name)
            #     st.success("✅ Image processed!")
            #     st.json(result)
