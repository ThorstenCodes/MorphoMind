import os
from params import LOCAL_DATA_PATH
from pathlib import Path
from google.cloud import storage
from tqdm.std import tqdm

def create_folder_structure(plate_number):
        """
        Check for folder structure and create it when needed.
        """
        ## Check if data folders exists. If not, create it.
        if not os.path.exists(LOCAL_DATA_PATH):
            os.makedirs(LOCAL_DATA_PATH)
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'processed'))

        if not os.path.exists(Path(LOCAL_DATA_PATH).joinpath(plate_number)):
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number))
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'processed'))

        if not os.path.exists(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw')):
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))

        if not os.path.exists(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'processed')):
            os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'processed'))

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """
    Download a file from GCS. Is called blob so is generic but will retrieve the SQLite DB.

    :param bucket_name: The name of the bucket
    :param source_blob_name: The name of the blob
    :param destination_file_name: The name of the file to save the blob to
    """
    # Initialize a client
    storage_client = storage.Client()
    # Get the bucket
    bucket = storage_client.bucket(bucket_name)
    # Get the blob
    blob = bucket.blob(source_blob_name)
    # Download the blob to a destination file
    with open(destination_file_name, 'wb') as f:
        with tqdm.wrapattr(f, "write", total=blob.size) as file_obj:
            storage_client.download_blob_to_file(blob, file_obj)