import pandas as pd
from pathlib import Path
import sqlite3
from params import *
from utils import create_folder_structure, download_blob, big_query_read, big_query_write


class Plate:
    def __init__(self, plate_number):
        self.plate_number = plate_number
        self.chem_cols = ['BROAD_ID', 'CPD_NAME', 'CPD_NAME_TYPE', 'SOURCE_NAME', 'CPD_SMILES']
        self.well_cols = ['Metadata_Well', 'Metadata_ASSAY_WELL_ROLE', 'Metadata_mmoles_per_liter']

    def run(self):
        """
        Load the data from the local or remote source.
        """
        print(f'Trying to load local data for plate {self.plate_number}...')

        processed_small_file = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'processed', f'{self.plate_number}_small.csv')

        if processed_small_file.is_file():
            self.processed_pictures_df = pd.read_csv(processed_small_file)
            print(f'✅ Loaded local Pictures Processed Data sucessfully')
        else:
            self.get_processed_data(processed_small_file)


    def get_processed_data(self, saving_path):

        print(f'Local processed file not found. Trying to retrieve data from Big Query...')
        try:
            full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{self.plate_number}_small"
            data = big_query_read(GCP_PROJECT, full_table_name)
            data = data.to_dataframe()
            print(f'✅ Processed Data retrieved from Big Query successfully.')

            data.to_csv(saving_path, header=True, index=False)
            print(f'✅ Processed Data saved succesfully.')

            self.processed_pictures_df = data

        except:
            print(f'Big Query for not found. Retrieving small dataset raw data from remote server...')
            create_folder_structure(self.plate_number)

            sqlite_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', f'{self.plate_number}.sqlite')
            if not sqlite_path.is_file():
                self.retrieve_sqlite()
            conn = sqlite3.connect(sqlite_path)

            self.load_well_annotations()
            self.load_pictures_data(conn)
            self.load_cells_data(conn)
            self.merge_picture_data()
            conn.close()
            self.save()

    def load_well_annotations(self):
## Check that mean_well_profile.csv exists. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', 'mean_well_profiles.csv')

        if data_query_cache_path.is_file():
            print('Loading Well Profiles from local CSV...')
            self.well_df = pd.read_csv(data_query_cache_path)
        else:
            print('Loading Well Profiles from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/raw/mean_well_profiles.csv',
                        data_query_cache_path
                        )
            self.well_df = pd.read_csv(data_query_cache_path)

        self.well_df = self.well_df[self.well_cols]
        self.well_df.rename(columns={'Metadata_Well': 'Well',
                                                    'Metadata_ASSAY_WELL_ROLE': 'Role',
                                                    'Metadata_mmoles_per_liter': 'MMoles'}, inplace=True)
        self.well_df['Plate'] = self.plate_number

    def load_pictures_data(self, conn):
## Create Images DF
        query = """
                SELECT TableNumber, Image_URL_OrigAGP, Image_URL_OrigDNA,
                Image_URL_OrigER, Image_URL_OrigMito, Image_URL_OrigRNA,
                Image_Count_Cells
                FROM Image
                """
        cursor = conn.execute(query)
        data = cursor.fetchall()
        self.pictures_df = pd.DataFrame(data, columns=['ImageID', 'PhGolgi', 'Hoechst', 'ERSyto', 'Mito', 'ERSytoBleed', 'CellCount'])

    def load_cells_data(self, conn):
## Create Cells DF
        query = """
                SELECT TableNumber as ImageID, AVG(Cells_AreaShape_Area) as MeanArea
                FROM Cells
                GROUP BY TableNumber
                """
        cursor = conn.execute(query)
        data = cursor.fetchall()
        self.cells_df = pd.DataFrame(data, columns=["".join(i[0].split('_')) for i in cursor.description])

    def retrieve_sqlite(self):
## Check that sqlite db exists locally. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', f'{self.plate_number}.sqlite')

        if data_query_cache_path.is_file():
            print('Loading SQLite DB from local DB...')
        else:
            print('Loading SQLite DB from remote DB...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/raw/{self.plate_number}.sqlite',
                        data_query_cache_path)

    def merge_picture_data(self):
        """
        Clean the data.
        """
        print('Extracting well from picture file name...')
        wells_df = self.pictures_df.drop(columns=['CellCount','ImageID']).applymap(lambda x: x.split('/')[-1].split('_')[1])
        wells_df['Well'] = wells_df.apply(lambda row: row.unique()[0] if row.nunique()==1 else 0, axis=1)

        print('Extracting photo id from picture file name...')
        photo_number_df = self.pictures_df.drop(columns=['CellCount','ImageID']).applymap(lambda x: x.split('/')[-1].split('_')[2])
        photo_number_df['PhotoNumber'] = photo_number_df.apply(lambda row: int(row.unique()[0][1]) if row.nunique()==1 else float('NaN'), axis=1)
        print('Converting photo path for training...')

        root_path = f'https://storage.cloud.google.com/{BUCKET_NAME}/{self.plate_number}/raw/pictures/'
        self.pictures_df['PhGolgi'] = self.pictures_df['PhGolgi'].apply(lambda x: (f'{root_path}{self.plate_number}-Ph_golgi/{x.split("/")[-1]}'))
        self.pictures_df['Hoechst'] = self.pictures_df['Hoechst'].apply(lambda x: (f'{root_path}{self.plate_number}-Hoechst/{x.split("/")[-1]}'))
        self.pictures_df['ERSyto'] = self.pictures_df['ERSyto'].apply(lambda x: (f'{root_path}{self.plate_number}-ERSyto/{x.split("/")[-1]}'))
        self.pictures_df['Mito'] = self.pictures_df['Mito'].apply(lambda x: (f'{root_path}{self.plate_number}-Mito/{x.split("/")[-1]}'))
        self.pictures_df['ERSytoBleed'] = self.pictures_df['ERSytoBleed'].apply(lambda x: (f'{root_path}{self.plate_number}-ERSytoBleed/{x.split("/")[-1]}'))

        print('Concatenating...')
        self.concat_df = pd.concat([
            self.pictures_df,
            wells_df['Well'],
            photo_number_df['PhotoNumber'].astype('int32')
        ],
        axis = 1)

        self.concat_df[['CellCount']] = self.concat_df[['CellCount']].astype('int32')
        self.well_df[['MMoles']] = self.well_df[['MMoles']].astype('float32')

        self.processed_df = self.concat_df.merge(self.well_df).fillna('None').merge(self.cells_df, on='ImageID').drop(columns=['ImageID'])

        print('✅ Data Merged')

    def save(self):
        saving_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'processed', f'{self.plate_number}_small.csv')

        self.save_df = self.processed_df

        self.save_df.to_csv(saving_path, index=False)
        print(f'✅ Data saved to {saving_path}')
        # print('Now, storing data in Big Query...')
        # full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{self.plate_number}_small"
        # big_query_write(GCP_PROJECT, full_table_name, self.save_df)
        # print(f'✅ Table uploaded to Big Query!')


if __name__ == '__main__':

    plate = Plate('24585')
    plate.run()

    plate = Plate('24639')
    plate.run()

    plate = Plate('24277')
    plate.run()

#     PLATES = [
#     24302, 24585, 24639, 24774, 25576, 25689, 25935, 26166, 26545, 26672,
#     24277, 24564, 24644, 24750, 25572, 25911, 26203, 26794, 24792, 26576
# ]
#     for plate in PLATES:
#         plate = Plate(f'{plate}')
#         plate.run()
