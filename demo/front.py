import streamlit as st
import numpy as np
import requests
from PIL import Image


st.set_page_config(page_title='Morpho Minds',
                   page_icon='microbe')

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



url = 'https://taxifare-s6ijqaeqvq-ew.a.run.app/predict'

st.title("Morpho Minds")

st.write('Predicting cell morphology from pictures.')

file = st.file_uploader('Upload a picture of cells',)

if file is not None:
    image = Image.open(file)
    img_array = convert_image(image)
    response = request_number_prediction(img_array)

st.text(response.json())
