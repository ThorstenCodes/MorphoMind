import streamlit as st
import numpy as np
import requests
from PIL import Image
import base64

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

# Customize color of text
st.markdown("""
<style>
body {
    color: #ffffff; /* Change all text to white */
}

h1, h2, h3, h4, h5, h6, p {
    color: #ffffff !important; /* Make sure headers and paragraphs are included */
}
.streamlit-expanderHeader {
    background-color: white;
    color: grey; # Adjust this for expander header color
}
.streamlit-expanderContent {
    background-color: white;
    color: black; # Expander content color
}
</style>
""", unsafe_allow_html=True)


def convert_image(image):
    image = image.resize((224, 224), Image.Resampling.NEAREST)
    image_array = np.array(image)
    return image_array

def request_number_prediction(img_array):
    params = {
        'image': img_array.tolist()
    }

    response = requests.get('https://taxifare-s6ijqaeqvq-ew.a.run.app/predict', params=params)

    return response

def transform_unit_for_area(image_array, width, height):
    x = image_array.shape[0]
    y = image_array.shape[1]
    area_converted = width*height*x*y

    return area_converted



url = 'https://taxifare-s6ijqaeqvq-ew.a.run.app/predict'

st.title("Morpho Minds")

st.write('Predicting cell morphology from pictures.')

choice = st.selectbox('Select what you want to determine:', ['Cell Number', 'Cell Area', 'Cell Number & Cell Area'])

# Ask the user to input the resolution in 'width x height' format
resolution_input = st.text_input("Enter the resolution in 'width x height' format (e.g., 500 x 400):")
unit = st.selectbox("Select the unit of measurement:",
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


file = st.file_uploader('Upload a picture of cells',)

if file is not None:
    image = Image.open(file)
    img_array = convert_image(image)
    response = request_number_prediction(img_array)

    if response.status_code == 200:
        data = response.json()  # This line is moved up here to ensure `data` is defined before you check conditions

        if choice == 'Cell Number':
            cell_number = data.get("cell_number", "N/A")  # Provide a default value in case the key doesn't exist
            st.markdown(f"Your uploaded image contains {cell_number} cells.", unsafe_allow_html=True)

        elif choice == 'Cell Area':
            cell_area = data.get("cell_area", "N/A")  # Provide a default value
            if resolution_input == True:
                st.markdown(f"{transform_unit_for_area} square {unit} of your image are covered with cells.")
            else:
                st.markdown(f"{cell_area} square pixel of your image are covered with cells.", unsafe_allow_html=True)

        elif choice == 'Cell Number & Cell Area':
            cell_number = data.get("cell_number", "N/A")
            cell_area = data.get("cell_area", "N/A")
            st.markdown(f"Your uploaded image contains {cell_number} cells.", unsafe_allow_html=True)
            if resolution_input == True:
                st.markdown(f"{transform_unit_for_area} square {unit} of your image are covered with cells.")
            else:
                st.markdown(f"{cell_area} square pixel of your image are covered with cells.", unsafe_allow_html=True)
    else:
        st.error("Failed to get a response from the prediction service.")



####### Calculate real area
# user input microscope pixel
# take pixel size from numpy array
# calculation before print out.
