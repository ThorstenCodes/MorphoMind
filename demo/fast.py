import pandas as pd
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import io
from typing import List
import numpy as np
from PIL import Image
from tensorflow.keras import models


app = FastAPI()
app.state.model = models.load_model('final_model.keras')
# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def root():

    response = {
    'greeting': 'HOLA PEPE'
    }

    return response
class ImageData(BaseModel):
    image_np: list

@app.post("/predict_number")
async def predict_number(image_data: ImageData):
    image_np = np.array(image_data.image_np)

    img_array_expanded = np.expand_dims(image_np, axis=0)
    print(img_array_expanded.shape)
    predictions = float(app.state.model.predict(img_array_expanded))
    return JSONResponse(content={"predictions": predictions})
