import os

BUCKET_NAME = os.environ.get('BUCKET_NAME')
PLATE_NUMBER = os.environ.get('PLATE_NUMBER')
LOCAL_DATA_PATH = os.path.join(os.path.expanduser('~'), ".morpho_minds_data")
