import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from tensorflow.keras import models


app = FastAPI()
app.state.model_counter = models.load_model('final_counter_model.keras')
app.state.model_area = models.load_model('final_area_model.keras')

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
    predictions = float(app.state.model_counter.predict(img_array_expanded))
    return JSONResponse(content={"predictions": predictions})


@app.post('/predict_area')
async def predict_area(image_tensor: ImageData):
    image_tensor = np.array(image_tensor.image_np)
    image_tensor = image_tensor/65535
    img_array_expanded = np.expand_dims(image_tensor, axis=0)
    predictions = float(app.state.model_area.predict(img_array_expanded))
    return JSONResponse(content={"predictions_area": predictions})
