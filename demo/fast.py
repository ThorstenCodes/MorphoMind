import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from tensorflow.keras import models


app = FastAPI()
# app.state.model_cells_numbers = models.load_model('testing_model_numbers.keras')
# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# http://127.0.0.1:8000/predict?pickup_datetime=2012-10-06 12:10:20&pickup_longitude=40.7614327&pickup_latitude=-73.9798156&dropoff_longitude=40.6513111&dropoff_latitude=-73.8803331&passenger_count=2
# @app.get("/predict_number")
# def predict(
#         image: np.array,  # Image to be classified
#     ):
#     """
#     Predicts .
#     Assumes `image` is the Hoechst Channel and is provided as a numpy array.
#     """

#     X_pred_processed = image.reshape(1, 224, 224, 1)

#     cells_prediction = int(app.state.model.predict(X_pred_processed)[0][0])
#     return{'cells_amount': cells_prediction}

@app.get("/")
def root():

    response = {
    'greeting': 'sfasdfjnaskdjfnasjkdfnajds'
    }

    return response
