import streamlit as st
import pytesseract
from PIL import Image
import easyocr
import re
import pandas as pd

# Define input and output file paths
input_image = "path/to/your/image.jpg"  # Replace with your image file path
output_csv = "output.csv"

# Define regions for OCR (x1, y1, x2, y2)
FIELD_POSITIONS = {
    "Name of beneficiary": (515, 491, 817, 523),
    "Mobile": (554, 791, 914, 876),
    "Date": (1118, 243, 1365, 311),  # Coordinates for Date field
    "Record No.": (273, 246, 446, 295),
}

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

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

# Function to extract text from image regions using EasyOCR
def extract_text_from_image(image_path, field_positions):
    image = Image.open(image_path)

    extracted_data = {}

    for field_name, coords in field_positions.items():
        cropped_region = image.crop(coords)
        cropped_region.save(f'{field_name}.jpg')  # Save cropped region for debugging

        result = reader.readtext(f'{field_name}.jpg')  # Get OCR result from the region
        text = " ".join([item[1] for item in result])

        if field_name == "Mobile":
            text = improve_number_detection(text)

        if field_name == "Date":
            text = correct_ocr_date(text)
            text = convert_to_ddmmyyyy_format(text)

        extracted_data[field_name] = text.strip()

    return extracted_data

# Function to improve number extraction for mobile numbers
def improve_number_detection(extracted_text):
    digits_only = re.sub(r'\D', '', extracted_text)

    if len(digits_only) < 10:
        digits_only = '8' + digits_only  # Assuming '8' as the prefix for India
    return digits_only

# Save extracted data to CSV
def save_to_csv(data, output_path, input_filename):
    # Create a DataFrame with the required column order and 'Sr.No.' as the index
    formatted_data = {
        "Sr.No.": [1],
        "Filename": [input_filename],
        "Name of beneficiary": [data.get("Name of beneficiary", "")],
        "Record No.": [data.get("Record No.", "")],
        "Date of document": [convert_to_ddmmyyyy_format(data.get("Date", ""))],
        "Mobile": [data.get("Mobile", "")],
    }
    df = pd.DataFrame(formatted_data)
    
    # Append to CSV, creating the file if it doesn't exist
    df.to_csv(output_path, mode='a', header=not pd.io.common.file_exists(output_path), index=False)

# Streamlit app to handle file input
def main():
    st.title("Document OCR Extraction")

    # Display strong message to the user
    st.warning("""
    **Important Notice:**
    
    Please convert your PDF to JPG format using the following tool:  
    [https://www.ilovepdf.com/pdf_to_jpg](https://www.ilovepdf.com/pdf_to_jpg)
    
    **Only JPG images are accepted!**  
    Make sure your file is in JPG format before uploading. Any other format will not be processed.
    """)

    uploaded_file = st.file_uploader("Choose a JPG file", type=["jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Image', use_column_width=True)

        # Process the image and generate output CSV
        extracted_data = extract_text_from_image(uploaded_file, FIELD_POSITIONS)
        st.write(extracted_data)

        # Save the extracted data to CSV
        save_to_csv(extracted_data, output_csv, uploaded_file.name)

        st.success(f"Data has been successfully extracted and saved to {output_csv}")

        # Display the contents of the CSV to the user
        df = pd.read_csv(output_csv)
        st.write(df)

# Run the Streamlit app
if __name__ == "__main__":
    main()
