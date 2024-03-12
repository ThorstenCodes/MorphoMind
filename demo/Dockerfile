FROM python:3.10.6-slim

WORKDIR /app

COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD uvicorn fast:app --reload --host 0.0.0.0 --port $PORT
