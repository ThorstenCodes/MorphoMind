import streamlit as st
import numpy as np
import requests
from PIL import Image
import json
from json import JSONEncoder
import pickle
import io

st.set_page_config(page_title='Morpho Minds',
                   page_icon='microbe')

# Function to convert image to numpy array and resize it
def process_image(image):
    image = image.resize((224, 224))  # Resize image to required size
    image_np = np.array(image)
    return image_np.tolist()

# Function to send image to FastAPI for processing
def predict_image(image_np):

    url = "https://morpho-minds-predictor-api-s6ijqaeqvq-ey.a.run.app/predict_number"
    payload = {"image_np": image_np}
    response = requests.post(url, json=payload)
    predictions = response.json()["predictions"]
    return predictions

st.title("Morpho Minds")

st.write('Predicting cell morphology from pictures.')

file = st.file_uploader('Upload a picture of cells',)

if file is not None:
    image = Image.open(file)

    if st.button("Predict"):
        image_np = process_image(image)
        predictions = predict_image(image_np)
        st.write("Predictions:", predictions)
