import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import easyocr
import re

# Function to correct OCR misinterpretations in dates
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

# Function to convert date into DD/MM/YYYY format
def convert_to_ddmmyyyy_format(extracted_date):
    cleaned_date = re.sub(r'[^a-zA-Z0-9\s-]', '', extracted_date)
    cleaned_date = correct_ocr_date(cleaned_date)

    month_mapping = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
    }

    date_parts = cleaned_date.split('-')

    if len(date_parts) == 3:
        day = date_parts[0]
        month_str = date_parts[1]
        year = date_parts[2]

        month = month_mapping.get(month_str, "00")

        if len(day) == 2 and len(year) == 4:
            return f"{day}/{month}/{year}"
    return extracted_date

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Function to improve number extraction for mobile numbers
def improve_number_detection(extracted_text):
    digits_only = re.sub(r'\D', '', extracted_text)

    if len(digits_only) < 10:
        digits_only = '8' + digits_only  # Assuming '8' as the prefix for India
    return digits_only

# Function to extract text from image regions using EasyOCR
def extract_text_from_image(image_path, field_positions):
    image = Image.open(image_path)

    # Correct image orientation before extracting text
    result = pytesseract.image_to_osd(image)
    if 'Rotate: 180' in result:
        image = image.rotate(180, expand=True)

    extracted_data = {}

    for field_name, coords in field_positions.items():
        cropped_region = image.crop(coords)

        result = reader.readtext(cropped_region)  # Get OCR result from the region
        text = " ".join([item[1] for item in result])

        if field_name == "Mobile":
            text = improve_number_detection(text)

        if field_name == "Date":
            text = correct_ocr_date(text)
            text = convert_to_ddmmyyyy_format(text)

        extracted_data[field_name] = text.strip()

    return extracted_data

# Save extracted data to CSV
def save_to_csv(data, output_path):
    formatted_data = {
        "File name": "image.jpg",  # Replace with your image name
        "Name of beneficiary": data.get("Name of beneficiary", ""),
        "Record No.": data.get("Record No.", ""),
        "Date of document": convert_to_ddmmyyyy_format(data.get("Date", "")),
        "Mobile": data.get("Mobile", ""),
    }
    df = pd.DataFrame([formatted_data])
    df.to_csv(output_path, index=False)

# Streamlit app layout
st.title("OCR Data Extraction")

# Upload image
uploaded_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Image processing logic
    FIELD_POSITIONS = {
        "Name of beneficiary": (515, 491, 817, 523),
        "Mobile": (554, 791, 914, 876),
        "Date": (1118, 243, 1365, 311),
        "Record No.": (273, 246, 446, 295),
    }
    
    # Save the uploaded image
    with open("uploaded_image.jpg", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract text from image and process
    extracted_data = extract_text_from_image("uploaded_image.jpg", FIELD_POSITIONS)
    save_to_csv(extracted_data, "output.csv")
    
    # Load and display the DataFrame
    df = pd.read_csv("output.csv")
    st.write(df)
    
    # Provide the download link for the CSV
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name='output.csv',
        mime='text/csv'
    )
