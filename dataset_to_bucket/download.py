import os
import requests
import zipfile
from pathlib import Path
from tqdm.std import tqdm
import shutil
from google.cloud import storage
import tarfile

LOCAL_DATA_PATH = os.path.join(os.path.expanduser('~'), ".morpho_minds_data")
BUCKET_NAME = 'cell_profiles_morpho_minds'

PLATES = [
    24302, 24585, 24639, 24774, 25576, 25689, 25935, 26166, 26545, 26672,
    26794, 26203, 25911, 25572, 24750, 24564, 24277, 24644, 24792, 26576
]


CHANNELS = [
    'Hoechst', 'ERSyto', 'ERSytoBleed', 'Ph_golgi', 'Mito'
    ]

preprocessed_data_urls = [f'https://ftp.cngb.org/pub/gigadb/pub/10.5524/100001_101000/100351/Plate_{i}.tar.gz' for i in PLATES]
pictures_urls = {plate:[f'https://cildata.crbs.ucsd.edu/broad_data/plate_{plate}/{plate}-{channel}.zip'
                for channel in CHANNELS] for plate in PLATES}

def create_folder_structure(plate_number):
    """
    Check for folder structure and create it when needed.
    """
    ## Check if data folders exists. If not, create it.
    if not os.path.exists(LOCAL_DATA_PATH):
        os.makedirs(LOCAL_DATA_PATH)
        os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))

    if not os.path.exists(Path(LOCAL_DATA_PATH).joinpath(plate_number)):
        os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number))
        os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))

    if not os.path.exists(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw')):
        os.makedirs(Path(LOCAL_DATA_PATH).joinpath(plate_number, 'raw'))

def download_dataset(url, plate_number):
    saving_path = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw')
    if not os.path.exists(saving_path):
        os.makedirs(saving_path)

    # Download the file
    try:
        file_path = Path(saving_path).joinpath(f'Plate_{plate_number}.tar.gz')
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                with tqdm.wrapattr(f, "write", total=int(r.headers.get('content-length'))) as file_obj:
                    for chunk in r.iter_content(chunk_size=8192):
                        file_obj.write(chunk)
        print(f"Downloaded {url} to {file_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def unzip_dataset(plate_number):
# Unzip the file
    print('Unzipping...')
    file_path = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw', f'Plate_{plate_number}.tar.gz')
    uncompressed_dir = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw', 'temp')
    if not file_path.exists():
        print('File does not exist')

    tar = tarfile.open(file_path, "r:gz",)
    tar.extractall(uncompressed_dir)
    tar.close()
    print(f"Unzipped to {uncompressed_dir}")

    files_path = uncompressed_dir.joinpath('gigascience_upload', f'Plate_{plate_number}')
    sqlite_path = files_path.joinpath('extracted_features', f'{plate_number}.sqlite')
    profiles_path = files_path.joinpath('profiles', 'mean_well_profiles.csv')
    save_path = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw')
    print(f"Moving files...")
    shutil.move(sqlite_path, save_path)
    shutil.move(profiles_path, save_path)
    print("Deleting temp files...")
    shutil.rmtree(uncompressed_dir)
    os.remove(file_path)
    print("Done.")

def download_pictures(urls, plate_number):
    for url in urls:
        channel = url.split("/")[-1].split("-")[1].split(".")[0]
        file_name = url.split("/")[-1]
        saving_path = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw')
        print(f'Downloading pictures for plate {plate_number} and channel {channel}...')

        if not os.path.exists(saving_path):
            os.makedirs(saving_path)

        # Download the file
        try:
            file_path = Path(saving_path).joinpath(f'{file_name}')
            if not file_path.exists():
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        with tqdm.wrapattr(f, "write", total=int(r.headers.get('content-length'))) as file_obj:
                            for chunk in r.iter_content(chunk_size=8192):
                                file_obj.write(chunk)
                print(f"Downloaded {url} to {file_path}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def unzip_pictures(plate_number):
    for channel in CHANNELS:
        print(f'Unzipping pictures for channel {channel}...')
        zip_file_path = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw', f'{plate_number}-{channel}.zip')
        if not zip_file_path.exists():
            print('File does not exist')
        zip_uncompressed_dir = Path(LOCAL_DATA_PATH).joinpath(str(plate_number), 'raw', 'pictures')
        z = zipfile.ZipFile(zip_file_path)
        z.extractall(zip_uncompressed_dir)
        print(f"Unzipped to {zip_uncompressed_dir}")
        print("Deleting temp files...")
        os.remove(zip_file_path)
        print("Done.")

def upload_folder_to_bucket(bucket_name, source_folder_path, plate_number):
    # Initialize Google Cloud Storage client
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    print(f"Uploading {source_folder_path} to {bucket_name}...")
    counter = 0
    try:
        # Walk through the source folder and upload files to the bucket
        for root, dirs, files in os.walk(source_folder_path):
            for file in files:
                # Get the local file path
                local_file_path = os.path.join(root, file)
                # Get the relative file path (stripping the source_folder_path)
                relative_file_path = os.path.relpath(local_file_path, source_folder_path)
                # Define the destination blob path in the bucket
                destination_blob_path = os.path.join(f'{plate_number}', relative_file_path).replace("\\", "/")
                # Create a blob in the bucket
                blob = bucket.blob(destination_blob_path)
                # Upload the file
                blob.upload_from_filename(local_file_path)
                counter = counter + 1
                if counter == 200:
                    print("200 files uploaded...")
                    counter = 0
            print(f"✅ {source_folder_path} uploaded to {bucket_name}")
        # Delete local folder
        shutil.rmtree(source_folder_path)
    except Exception as e:
        print(f"Failed to upload {source_folder_path} to {bucket_name}: {e}")

# for i, plate in enumerate(PLATES):
#    create_folder_structure(f'{plate}')
#    download_dataset(preprocessed_data_urls[i], plate)
    # unzip_dataset(plate)
#    download_pictures(pictures_urls[plate], plate)
#    unzip_pictures(plate)
#    upload_folder_to_bucket(BUCKET_NAME, Path(LOCAL_DATA_PATH).joinpath(str(plate)), plate)

upload_folder_to_bucket(BUCKET_NAME, Path(LOCAL_DATA_PATH).joinpath(str(24277)), '24277')
