"""
Author : Janarddan Sarkar
file_name : mistral_ocr_st.py 
date : 10-03-2025
description : 
"""
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

# Load environment variables
load_dotenv(find_dotenv())
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

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})")
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    markdowns: list[str] = []
    for page in ocr_response.pages:
        image_data = {img.id: img.image_base64 for img in page.images}
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))
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


def process_image(image_bytes, file_name):
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


# Streamlit UI
st.title("Mistral OCR")

uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    file_type = uploaded_file.type
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    if st.button("Submit"):
        st.write(f"**Processing file:** {file_name}")

        if "pdf" in file_type:
            pdf_response = process_pdf(file_bytes, file_name)
            st.markdown(get_combined_markdown(pdf_response))
        else:
            result = process_image(file_bytes, file_name)
            st.json(result)
