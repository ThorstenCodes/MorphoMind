import os

MODEL_TARGET = os.environ.get('MODEL_TARGET')
GCP_PROJECT = os.environ.get('GCP_PROJECT')
GCP_REGION = os.environ.get('GCP_REGION')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
BQ_REGION = os.environ.get('BQ_REGION')
BQ_DATASET = os.environ.get('BQ_DATASET')
PLATE_NUMBER = os.environ.get('PLATE_NUMBER')

LOCAL_DATA_PATH = os.path.join(os.path.expanduser('~'), ".morpho_minds_data")
