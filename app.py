import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import easyocr
import re
import numpy as np

# Define regions for OCR (x1, y1, x2, y2)
FIELD_POSITIONS = {
    "Name of beneficiary": (515, 491, 817, 523),
    "Mobile": (554, 791, 914, 876),
    "Date": (1118, 243, 1365, 311),
    "Record No.": (273, 246, 446, 295),
}

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Helper functions
def pil_to_np_array(pil_image):
    """Convert a PIL Image to a NumPy array."""
    return np.array(pil_image)

def correct_ocr_date(ocr_output):
    corrections = {
        "O": "0", "I": "1", "l": "1", "Z": "2", "S": "5", "B": "8", "G": "6", 
        "q": "9", "ozz": "022", "zz": "22", "on": "01", "iO": "10", "O5": "05", "lo": "10"
    }

    corrected_output = ocr_output
    while True:
        previous_output = corrected_output
        for wrong, right in corrections.items():
            corrected_output = corrected_output.replace(wrong, right)

        if corrected_output == previous_output:
            break

    return corrected_output

def convert_to_ddmmyyyy_format(extracted_date):
    cleaned_date = re.sub(r'[^a-zA-Z0-9\s-]', '', extracted_date)
    cleaned_date = correct_ocr_date(cleaned_date)

    month_mapping = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
    }

    date_parts = cleaned_date.split('-')
    if len(date_parts) == 3:
        day, month_str, year = date_parts
        month = month_mapping.get(month_str, "00")
        if len(day) == 2 and len(year) == 4:
            return f"{day}/{month}/{year}"
    return extracted_date

def improve_number_detection(extracted_text):
    digits_only = re.sub(r'\D', '', extracted_text)
    if len(digits_only) < 10:
        digits_only = '8' + digits_only
    return digits_only

def extract_text_from_image(image, field_positions, filename):
    extracted_data = {"File Name": filename}

    for field_name, coords in field_positions.items():
        cropped_region = image.crop(coords)
        cropped_np = pil_to_np_array(cropped_region)  # Convert to NumPy array
        result = reader.readtext(cropped_np)  # OCR for the region
        text = " ".join([item[1] for item in result])

        if field_name == "Mobile":
            text = improve_number_detection(text)
        if field_name == "Date":
            text = correct_ocr_date(text)
            text = convert_to_ddmmyyyy_format(text)

        extracted_data[field_name] = text.strip()

    return extracted_data

def save_to_csv(data, output_path):
    df = pd.DataFrame([data])
    df.to_csv(output_path, index=False)

# Streamlit UI
def main():
    st.title("Document Reader with OCR")
    st.write("Upload an image to extract key information.")

    uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        filename = uploaded_image.name
        st.image(image, caption=f"Uploaded Image: {filename}", use_column_width=True)

        # Process the image
        with st.spinner("Processing the image..."):
            extracted_data = extract_text_from_image(image, FIELD_POSITIONS, filename)

        st.success("Extraction completed!")
        st.write("Extracted Data:")
        st.json(extracted_data)

        # Save extracted data as CSV
        output_csv = "extracted_data.csv"
        save_to_csv(extracted_data, output_csv)

        with open(output_csv, "rb") as file:
            st.download_button(
                label="Download CSV",
                data=file,
                file_name="extracted_data.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
