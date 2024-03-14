FROM python:3.10.6-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY fast.py fast.py
COPY final_model.keras final_model.keras

CMD uvicorn fast:app --reload --log-level=debug --host 0.0.0.0 --port $PORT
