import pandas as pd
from pathlib import Path
import sqlite3
from params import *
from utils import create_folder_structure, download_blob, big_query_read, big_query_write


class Plate:
    def __init__(self, plate_number):
        self.plate_number = plate_number
        self.chem_cols = ['BROAD_ID', 'CPD_NAME', 'CPD_NAME_TYPE', 'SOURCE_NAME', 'CPD_SMILES']
        self.well_cols = ['Metadata_Well', 'Metadata_ASSAY_WELL_ROLE', 'Metadata_broad_sample', 'Metadata_mmoles_per_liter']

    def run(self):
        """
        Load the data from the local or remote source.
        """
        print(f'Trying to load local data for plate {self.plate_number}...')

        processed_pictures_file = Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'processed', f'{PLATE_NUMBER}_pictures.csv')
        processed_cells_file = Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'processed', f'{PLATE_NUMBER}_cells.csv')

        if processed_pictures_file.is_file():
            self.processed_pictures_df = pd.read_csv(processed_pictures_file)
            print(f'✅ Loaded local Pictures Processed Data sucessfully')
        else:
            self.get_processed_data('pictures', processed_pictures_file)

        if processed_cells_file.is_file():
            self.processed_cells_df = pd.read_csv(processed_cells_file)
            print(f'✅ Loaded local Cells Processed Data sucessfully')

        else:
            self.get_processed_data('cells', processed_cells_file)

    def get_processed_data(self, table_name, saving_path):

        print(f'Local processed file for {table_name} not found. Trying to retrieve data from Big Query...')
        try:
            full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{PLATE_NUMBER}_{table_name}"
            data = big_query_read(GCP_PROJECT, full_table_name)
            data = data.to_dataframe()
            print(f'✅ {table_name} Processed Data retrieved from Big Query successfully.')

            data.to_csv(saving_path, header=True, index=False)
            print(f'✅ {table_name} Processed Data saved succesfully.')

            if table_name == 'pictures':
                self.processed_pictures_df = data
            else:
                self.processed_cells_df = data

        except:
            print(f'Big Query for {table_name} not found. Retrieving {table_name} raw data from remote server...')
            create_folder_structure(self.plate_number)

            sqlite_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', f'{self.plate_number}.sqlite')
            if not sqlite_path.is_file():
                self.retrieve_sqlite()
            conn = sqlite3.connect(sqlite_path)

            if table_name == 'pictures':
                self.load_chemical_annotations()
                self.load_well_annotations()
                self.load_pictures_data(conn)
                self.merge_picture_data()
                conn.close()
                self.save('pictures')

            if table_name == 'cells':
                self.load_cells_data(conn)
                conn.close()
                self.clean_cells_data()
                breakpoint()
                self.save('cells')

    def load_chemical_annotations(self):
## Check that file chemical_compounds.csv exists locally. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath('chemical_annotations.csv')

        if data_query_cache_path.is_file():
            print('Loading Chemical Annotations from local CSV...')
            self.chem_df = pd.read_csv(data_query_cache_path)

        else:
            print('Loading Chemical Annotations from remote server...')
            download_blob(BUCKET_NAME,
                        'chemical_annotations.csv',
                        data_query_cache_path
                        )

            self.chem_df = pd.read_csv(data_query_cache_path)

        self.chem_df = self.chem_df[self.chem_cols]
        self.chem_df.rename(columns={'BROAD_ID': 'DrugID',
                                     'CPD_NAME': 'CPDName',
                                     'CPD_NAME_TYPE': 'CPDTypeName',
                                     'SOURCE_NAME': 'SourceName',
                                     'CPD_SMILES': 'CPDSmiles'}, inplace=True)

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
                                                    'Metadata_broad_sample': 'DrugID',
                                                    'Metadata_mmoles_per_liter': 'MMoles'}, inplace=True)

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
                SELECT TableNumber, Cells_AreaShape_Area, Cells_AreaShape_Compactness,
                Cells_AreaShape_Eccentricity, Cells_AreaShape_EulerNumber, Cells_AreaShape_Extent,
                Cells_AreaShape_FormFactor, Cells_AreaShape_MaxFeretDiameter, Cells_AreaShape_MinFeretDiameter,
                Cells_AreaShape_MeanRadius, Cells_AreaShape_MedianRadius, Cells_AreaShape_Orientation,
                Cells_AreaShape_Perimeter, Cells_AreaShape_Solidity, Cells_AreaShape_Zernike_0_0,
                Cells_Children_Cytoplasm_Count, Cells_Granularity_10_RNA
                FROM Cells
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
        self.pictures_df['PhGolgi'] = self.pictures_df['PhGolgi'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Ph_golgi', x.split('/')[-1])))
        self.pictures_df['Hoechst'] = self.pictures_df['Hoechst'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Hoechst', x.split('/')[-1])))
        self.pictures_df['ERSyto'] = self.pictures_df['ERSyto'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSyto', x.split('/')[-1])))
        self.pictures_df['Mito'] = self.pictures_df['Mito'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Mito', x.split('/')[-1])))
        self.pictures_df['ERSytoBleed'] = self.pictures_df['ERSytoBleed'].apply(lambda x: str(Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSytoBleed', x.split('/')[-1])))

        print('Concatenating...')
        self.concat_df = pd.concat([
            self.pictures_df,
            wells_df['Well'],
            photo_number_df['PhotoNumber'].astype('int32'),
        ],
        axis = 1)

        self.concat_df[['CellCount']] = self.concat_df[['CellCount']].astype('int32')
        self.well_df[['MMoles']] = self.well_df[['MMoles']].astype('float32')

        print('Identifying drugs used per well...')

        self.processed_pictures_df = self.concat_df.merge(self.well_df).merge(self.chem_df, how='left', on='DrugID').fillna('None')

        print('✅ Data Merged')

    def clean_cells_data(self):
        """
        Change the data types to int32 and float32.
        """
        int_cols = self.cells_df.select_dtypes('int64').columns
        float_cols = self.cells_df.select_dtypes('float64').columns

        self.cells_df[int_cols] = self.cells_df[int_cols].astype('int32')
        self.cells_df[float_cols] = self.cells_df[float_cols].astype('float32')

        self.cells_df = self.cells_df.fillna(0)

    def save(self, table):
        saving_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'processed', f'{PLATE_NUMBER}_{table}.csv')

        if table == 'pictures':
            self.save_df = self.processed_pictures_df
        else:
            self.save_df = self.cells_df

        self.save_df.to_csv(saving_path, index=False)
        print(f'✅ {table} Data saved to {saving_path}')
        print('Now, storing data in Big Query...')
        full_table_name = f"{GCP_PROJECT}.{BQ_DATASET}.{PLATE_NUMBER}_{table}"
        big_query_write(GCP_PROJECT, full_table_name, self.save_df)
        print(f'✅ {table} Table uploaded to Big Query!')


if __name__ == '__main__':
    plate = Plate(PLATE_NUMBER)
    plate.run()
