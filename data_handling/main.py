import pandas as pd
from pathlib import Path
import sqlite3
from params import *
from utils import create_folder_structure, download_blob, big_query_read, big_query_write


class Plate:
    def __init__(self, plate_number=None, chem_df=None, images_df=None, well_df=None, plate_df=None):
        self.plate_number = plate_number
        self.chem_df = chem_df
        self.images_df = images_df
        self.well_df = well_df
        self.plate_df = plate_df
        self.chem_cols = ['BROAD_ID', 'CPD_NAME', 'CPD_NAME_TYPE', 'SOURCE_NAME', 'CPD_SMILES']
        self.well_cols = ['Metadata_Well', 'Metadata_ASSAY_WELL_ROLE', 'Metadata_broad_sample', 'Metadata_mmoles_per_liter']

    def load(self):
        """
        Load the data from the local or remote source.
        """
        if MODEL_TARGET == 'local':
            print('Trying to load local data...')
            pictures_dir = Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'raw', 'raw_pictures')
            processed_file = Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'processed', f'{PLATE_NUMBER}_processed.csv')
            if not pictures_dir.is_dir():
                print('Local pictures not found. Please make sure the data is available in the local folder.')
                exit(1)
            elif not processed_file.is_file():
                print('Local processed file not found. Trying to retrieve data from Big Query...')
                try:
                    full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{PLATE_NUMBER}_processed"
                    data = big_query_read(GCP_PROJECT, full_table_name)
                    data = data.to_dataframe()
                    print('✅ Data retrieved from Big Query successfully.')

                    # Save it locally to accelerate the next queries!
                    self.processed_df = data.to_csv(processed_file, header=True, index=False)
                    print(f'✅ Data saved to {processed_file}')
                except:
                    print('Big Query data not found. Retrieving data from remote server...')
                    self.retrieve_data()
                    self.merge_data()
                    self.save()
            else:
                print('✅ Local data loaded successfully.')


        if MODEL_TARGET == 'prod':

            print('Malo')

    def retrieve_data(self):
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
            self.chem_df = pd.read_csv(data_query_cache_path)

        else:
            print('Loading Chemical Annotations from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/chemical_annotations.csv',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'chemical_annotations.csv')
                        )

            self.chem_df = pd.read_csv(data_query_cache_path)
        self.chem_df = self.chem_df[self.chem_cols]
        self.chem_df.rename(columns={'BROAD_ID': 'DrugID',
                                     'CPD_NAME': 'CPDName',
                                     'CPD_NAME_TYPE': 'CPDTypeName',
                                     'SOURCE_NAME': 'SourceName',
                                     'CPD_SMILES': 'CPDSmiles'}, inplace=True)

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
                SELECT Image_URL_OrigAGP, Image_URL_OrigDNA, Image_URL_OrigER, Image_URL_OrigMito, Image_URL_OrigRNA, Image_Count_Cells
                FROM Image
                """
        cursor = conn.execute(query)
        data = cursor.fetchall()
        self.images_df = pd.DataFrame(data, columns=['PhGolgi', 'Hoechst', 'ERSyto', 'Mito', 'ERSytoBleed', 'CellCount'])

        conn.close()

        ## Check that mean_well_profile.csv exists. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', 'mean_well_profiles.csv')
        data_query_cached_exists = data_query_cache_path.is_file()

        if data_query_cached_exists:
            print('Loading Well Profiles from local CSV...')
            self.well_df = pd.read_csv(data_query_cache_path)
        else:
            print('Loading Well Profiles from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/mean_well_profiles.csv',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', 'mean_well_profiles.csv')
                        )
            self.well_df = pd.read_csv(data_query_cache_path)
        self.well_df = self.well_df[self.well_cols]
        self.well_df.rename(columns={'Metadata_Well': 'Well',
                                                    'Metadata_ASSAY_WELL_ROLE': 'Role',
                                                    'Metadata_broad_sample': 'DrugID',
                                                    'Metadata_mmoles_per_liter': 'MMoles'}, inplace=True)

        print('✅ Data loaded successfully.')

        return self

    def merge_data(self):
        """
        Clean the data.
        """
        print('Extracting well from picture file name...')
        wells_df = self.images_df.drop(columns=['CellCount']).applymap(lambda x: x.split('/')[-1].split('_')[1])
        wells_df['Well'] = wells_df.apply(lambda row: row.unique()[0] if row.nunique()==1 else 0, axis=1)

        print('Extracting photo id from picture file name...')
        photo_number_df = self.images_df.drop(columns=['CellCount',]).applymap(lambda x: x.split('/')[-1].split('_')[2])
        photo_number_df['PhotoNumber'] = photo_number_df.apply(lambda row: int(row.unique()[0][1]) if row.nunique()==1 else float('NaN'), axis=1)

        print('Converting photo path for training...')
        self.images_df['PhGolgi'] = self.images_df['PhGolgi'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Ph_golgi', x.split('/')[-1])))
        self.images_df['Hoechst'] = self.images_df['Hoechst'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Hoechst', x.split('/')[-1])))
        self.images_df['ERSyto'] = self.images_df['ERSyto'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSyto', x.split('/')[-1])))
        self.images_df['Mito'] = self.images_df['Mito'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Mito', x.split('/')[-1])))
        self.images_df['ERSytoBleed'] = self.images_df['ERSytoBleed'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSytoBleed', x.split('/')[-1])))

        print('Concatenating...')
        self.concat_df = pd.concat([
            self.images_df,
            wells_df['Well'],
            photo_number_df['PhotoNumber'].astype('int32'),
        ],
        axis = 1)

        self.concat_df[['CellCount']] = self.concat_df[['CellCount']].astype('int32')
        self.well_df[['MMoles']] = self.well_df[['MMoles']].astype('float32')

        print('Identifying drugs used per well...')

        self.processed_df = self.concat_df.merge(self.well_df).merge(self.chem_df, how='left', on='DrugID').fillna('None')

        print('✅ Data Merged')


    def save(self):
        saving_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'processed', f'{PLATE_NUMBER}_processed.csv')
        self.processed_df.to_csv(saving_path, index=False)
        print(f'✅ Data saved to {saving_path}')
        print('Now, storing data in Big Query...')
        full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{PLATE_NUMBER}_processed"
        big_query_write(GCP_PROJECT, full_table_name, self.processed_df)


if __name__ == '__main__':
    plate = Plate(PLATE_NUMBER)
    plate.load()
