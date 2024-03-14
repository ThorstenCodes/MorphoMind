import streamlit as st
import numpy as np
import requests
from PIL import Image
import base64
import time


st.set_page_config(page_title='Morpho Minds',
                   page_icon='microbe')

def img_to_base64_str(file_path):
    """Reads an image file and converts it into a base64 string."""
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

#Function to set the background image using the base64 string
def set_bg_img_from_local(file_path):
    """Sets a background image from a local file by converting it to base64."""
    bin_str = img_to_base64_str(file_path)
    bg_img_style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
    }}
    </style>
    """
    st.markdown(bg_img_style, unsafe_allow_html=True)

# #Use the function with the path to your local JPG image
set_bg_img_from_local('demo/national-cancer-institute-L7en7Lb-Ovc-unsplash.jpg')
# set_bg_img_from_local('/Users/pepe/code/projects/MorphoMind/demo/national-cancer-institute-L7en7Lb-Ovc-unsplash.jpg')

st.markdown("""
<style>
body {
    color: #ffffff; /* Change all text to white */
}

p {
    font-size: 20px;
}
h1 {
    color: #ffffff !important; /* Make sure headers and paragraphs are included */
    font-size: 65px;
}

h2, h3, h4, h5, h6, p {
    color: #ffffff !important; /* Make sure headers and paragraphs are included */
    font-size: 18px;
}

/* Customize selectbox */
.stSelectbox > div {
    background-color: #f0f2f6; /* Background color */
    color: black; /* Text color */
}
.stButton > button {
    background-color: white !important;
}
.stButton > button > div > label,
.stButton > button > div > label > p,
.stButton > button > div > p {
    color: black !important; /* Ensure the text color is black */
}
.stSelectbox > label > div > p {
    font-size: 18px; /* Font size */
}

/* Customize text input */
.stTextInput > label > div > p {
    font-size: 18px; /* Font size */
}

/* Customize file uploader */
.stFileUploader > label > div > p > div > label {
    font-size: 18px; /* Font size */
}
.uploadedFileData {
    background-color: white !important;
    color: black !important;
}
</style>
""", unsafe_allow_html=True)


# Function to convert image to numpy array and resize it
def process_single_image(image):
    image = image.resize((224, 224))  # Resize image to required size
    image_np = np.array(image)
    return image_np.tolist()

def process_multi_images(files):
    preprocessed_images = []
    for file in files:
        img = Image.open(file)
        img = img.resize((224, 224))  # Resize image as per your requirement
        img_array = np.array(img)
        preprocessed_images.append(img_array)
    final = np.dstack(preprocessed_images)
    print(final.shape)
    return final.tolist()


# Function to send image to FastAPI for processing
def predict_image_cell_number(image_np):

    url = 'https://morpho-minds-predictor-api-s6ijqaeqvq-ey.a.run.app/predict_number'
    payload = {"image_np": image_np}
    response = requests.post(url, json=payload)
    predictions_number = response.json()["predictions"]
    return predictions_number

def predict_image_area(image_tensor):
    url = 'https://morpho-minds-predictor-api-s6ijqaeqvq-ey.a.run.app/predict_area'
    payload = {"image_np": image_tensor}
    response = requests.post(url, json=payload)
    predictions_area = response.json()["predictions_area"]
    return predictions_area

def transform_unit_for_area(image_array, width, height):
    x = image_array.shape[0]
    y = image_array.shape[1]
    area_converted = width*height*x*y

    return area_converted


st.title("Morpho Minds")

st.write('This AI tool allows you to upload TIFF images to determine the cell number or cell area on the image. The cell number and area are predicted by Deep Learning Models which have been trained on the xxx dataset. Have fun predicting from your pictures.')

# choice = st.selectbox('Select what you want to determine:', ['Cell Number', 'Cell Area'])

files = st.file_uploader('Upload files (.tif)',accept_multiple_files=True)

st.markdown("""
<style>
.big-font {
    font-size:30px;
}
</style>
""", unsafe_allow_html=True)


if files:
    if len(files) == 1:
        image = Image.open(files[0])
        if st.button("Predict Number of Cells"):
            image_np = process_single_image(image)
            with st.spinner('Wait for it...'):
                predictions = predict_image_cell_number(image_np)
            st.balloons()
            st.write(f'<p class="big-font">Predicted Nº of cells: {int(predictions)}</p>' , unsafe_allow_html=True)

    else:
        if st.button("Predict Area"):
            img_array = process_multi_images(files)
            with st.spinner('Wait for it...'):
                predictions = predict_image_area(img_array)
            st.balloons()
            st.write(f'<p class="big-font">Predicted Mean Area: {round(float(predictions), 2)} square pixels</p>', unsafe_allow_html=True)
