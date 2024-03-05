import pandas as pd
import numpy as np
from google.cloud import storage
import os
from pathlib import Path
from tqdm.std import tqdm
import sqlite3
from params import BUCKET_NAME, LOCAL_DATA_PATH, PLATE_NUMBER
from utils import create_folder_structure, download_blob

class Plate:
    def __init__(self, plate_number=None, chem_df=None, images_df=None, well_df=None, plate_df=None):
        self.plate_number = plate_number
        self.chem_df = chem_df
        self.images_df = images_df
        self.well_df = well_df
        self.plate_df = plate_df

    def load(self):
        """
        Load the all the plate data into different dataframes.
        """
        # Check for folder structure and create it when needed.
        create_folder_structure(self.plate_number)

        ## Check that file chemical_compounds.csv exists locally. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'chemical_annotations.csv')
        data_query_cached_exists = data_query_cache_path.is_file()

        if data_query_cached_exists:
            print('Loading Chemical Annotations from local CSV...')
            chem_df = pd.read_csv(data_query_cache_path)
        else:
            print('Loading Chemical Annotations from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/chemical_annotations.csv',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'chemical_annotations.csv')
                        )
            chem_df = pd.read_csv(data_query_cache_path)

        ## Check that sqlite db exists locally. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', f'{self.plate_number}.sqlite')
        data_query_cached_exists = data_query_cache_path.is_file()

        if data_query_cached_exists:
            print('Loading SQLite DB from local DB...')
        else:
            print('Loading SQLite DB from remote DB...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/{self.plate_number}.sqlite',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', f'{self.plate_number}.sqlite')
                        )

        conn = sqlite3.connect(data_query_cache_path)
        query = """
                SELECT Image_URL_OrigAGP, Image_URL_OrigDNA, Image_URL_OrigER, Image_URL_OrigMito, Image_URL_OrigRNA
                FROM Image
                """
        cursor = conn.execute(query)
        data = cursor.fetchall()
        images_df = pd.DataFrame(data, columns=[column[0] for column in cursor.description])

        ## Check that mean_well_profile.csv exists. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'mean_well_profiles.csv')
        data_query_cached_exists = data_query_cache_path.is_file()

        if data_query_cached_exists:
            print('Loading Well Profiles from local CSV...')
            well_df = pd.read_csv(data_query_cache_path)
        else:
            print('Loading Well Profiles from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/mean_well_profiles.csv',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'mean_well_profiles.csv')
                        )
            well_df = pd.read_csv(data_query_cache_path)
        self.chem_df = chem_df
        self.images_df = images_df
        self.well_df = well_df

        print('✅ Data loaded successfully.')

        return self

    def merge_data(self):
        """
        Merge the dataframes into one.
        """
        pass


if __name__ == '__main__':
    pepe = Plate('24277')
    pepe.load()
    print(pepe.plate_df.head())
