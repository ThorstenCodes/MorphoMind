from fastapi import FastAPI
import uvicorn
from PIL import Image
from tensorflow.keras.models import load_model as tf_load_model
from tensorflow.keras.utils import load_img, img_to_array
import numpy as np
from pydantic import BaseModel
from fastapi.responses import JSONResponse

app = FastAPI()

# Define a root `/` endpoint
@app.get('/')
def index():
    return {'greeting': 'Nice to see you, Boss!'}

@app.on_event("startup")
def load_model_on_startup():
    # Use the renamed TensorFlow's load_model function
    app.state.model = tf_load_model('model_3plate_ERSyto_ERSytobleed_Phgolgi_2024_03_13.keras')



class ImageData(BaseModel):
    image_np: list

class TensorData(BaseModel):
    image_tensor: list

@app.post("/predict_number")
async def predict_number(image_data: ImageData):
    image_np = np.array(image_data.image_np)
    img_array_expanded = np.expand_dims(image_np, axis=0)
    print(img_array_expanded.shape)
    predictions = float(app.state.model.predict(img_array_expanded))
    return JSONResponse(content={"predictions_number": predictions})

@app.post('/predict_area')
async def predict_area(tensor_data: TensorData):
        image_tensor = np.array(tensor_data.image_tensor)
        print(image_tensor.shape)
        predictions = float(app.state.model.predict(image_tensor))
        return JSONResponse(content={"predictions_area": predictions})
