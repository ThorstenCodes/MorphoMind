import streamlit as st
import numpy as np
import requests
from PIL import Image
import base64
from tensorflow.keras.utils import load_img, img_to_array


st.set_page_config(page_title='Morpho Minds',
                   page_icon='microbe')

def img_to_base64_str(file_path):
    """Reads an image file and converts it into a base64 string."""
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Function to set the background image using the base64 string
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

# Use the function with the path to your local JPG image
set_bg_img_from_local('/Users/thorsten/code/ThorstenCodes/MorphoMind/demo/national-cancer-institute-L7en7Lb-Ovc-unsplash.jpg')

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
</style>
""", unsafe_allow_html=True)



# Function to convert image to numpy array and resize it
def process_single_image(image):
    image = image.resize((224, 224))  # Resize image to required size
    image_np = np.array(image)
    return image_np.tolist()

def process_multi_images(files):
    # preprocessed_images = []
    # for file in files:
    #     img = load_img(file, target_size=(224, 224), color_mode='grayscale')
    #     img_array = img_to_array(img)
    #     img_array_expanded = np.expand_dims(img_array, axis=0)
    #     preprocessed_images.append(img_array_expanded)
    # image_tensor = np.concatenate(preprocessed_images, axis=0)
    # return image_tensor.tolist()
    preprocessed_images = []
    for file in files:
        try:
            img = Image.open(file)
            img = img.resize((224, 224))  # Resize image as per your requirement
            img_array = np.array(img)
            img_array_expanded = np.expand_dims(img_array, axis=0)
            preprocessed_images.append(img_array_expanded)
        except Exception as e:
            st.error(f"Error processing file {file.name}: {e}")
            continue

    if len(preprocessed_images) > 0:
        image_tensor = np.concatenate(preprocessed_images, axis=0)
        return image_tensor.tolist()
    else:
        st.error("No images could be processed.")
        return None

# Function to send image to FastAPI for processing
def predict_image_cell_number(image_np):

    url = "http://localhost:8000/predict_number/"
    payload = {"image_np": image_np}
    response = requests.post(url, json=payload)
    predictions_number = response.json()["predictions_number"]
    return predictions_number

def predict_image_area(image_tensor):
    url = "http://localhost:8000/predict_area/"
    payload = {"image_tensor": image_tensor}
    response = requests.post(url, json=payload)
    predictions_area = response.json()["predictions_area"]
    print(predictions_area)
    return predictions_area

def transform_unit_for_area(image_array, width, height):
    x = image_array.shape[0]
    y = image_array.shape[1]
    area_converted = width*height*x*y

    return area_converted



url = 'https://taxifare-s6ijqaeqvq-ew.a.run.app/predict'

st.title("Morpho Minds")

st.write('This AI tool allows you to upload TIFF images to determine the cell number or cell area on the image. The cell number and area are predicted by Deep Learning Models which have been trained on the xxx dataset. Have fun predicting from your pictures.')

choice = st.selectbox('Select what you want to determine:', ['Cell Number', 'Cell Area'])

# Ask the user to input the resolution in 'width x height' format
resolution_input = st.text_input("Enter the resolution of your image:", placeholder= "e.g.: pixel/unit x pixel/unit")
unit = st.selectbox("Select the unit of resolution:",
                    ('micrometers (µm)', 'nanometers (nm)', 'millimeters (mm)'))

try:
    # Split the input string on 'x' and strip any spaces
    width, height = [int(dim.strip()) for dim in resolution_input.split('x')]

    # Display the width and height to confirm
    st.write(f"Your resolution is {width*height} square {unit} per pixel")
except ValueError:
    # In case of an invalid input format
    st.write("Please enter the resolution in the correct format: 'width x height' (e.g., 500 x 400)")

# Now, 'width' and 'height' are stored as integers and can be used for further processing


files = st.file_uploader('Upload files (.tif)',accept_multiple_files=True)



if files:
    if len(files) == 1:
        image = Image.open(files[0])
        img_array = process_single_image(image)
    else:
        img_array = process_multi_images(files)

        if choice == 'Cell Number':
            predictions = predict_image_cell_number(img_array)
            cell_number = predictions.get("predictions_number")
            st.markdown(f"Your uploaded image contains {cell_number} cells.", unsafe_allow_html=True)

        elif choice == 'Cell Area':
            predictions = predict_image_area(img_array)
            cell_area = predictions.get("predictions_area")
            if resolution_input == True:
                st.markdown(f"{transform_unit_for_area} square {unit} of your image are covered with cells.")
            else:
                st.markdown(f"{cell_area} square pixel of your image are covered with cells.", unsafe_allow_html=True)
        else:
            st.error("Failed to get a response from the prediction service.")
