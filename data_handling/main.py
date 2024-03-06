import pandas as pd
from pathlib import Path
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
                SELECT Image_URL_OrigAGP, Image_URL_OrigDNA, Image_URL_OrigER, Image_URL_OrigMito, Image_URL_OrigRNA, Image_Count_Cells
                FROM Image
                """
        cursor = conn.execute(query)
        data = cursor.fetchall()
        images_df = pd.DataFrame(data, columns=['Ph-golgi', 'Hoechst', 'ERSyto', 'Mito', 'ERSytoBleed', 'CellCount'])

        conn.close()

        ## Check that mean_well_profile.csv exists. If not, download it.
        data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', 'mean_well_profiles.csv')
        data_query_cached_exists = data_query_cache_path.is_file()

        if data_query_cached_exists:
            print('Loading Well Profiles from local CSV...')
            well_df = pd.read_csv(data_query_cache_path)
        else:
            print('Loading Well Profiles from remote server...')
            download_blob(BUCKET_NAME,
                        f'{self.plate_number}/mean_well_profiles.csv',
                        Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'raw', 'mean_well_profiles.csv')
                        )
            well_df = pd.read_csv(data_query_cache_path)
        self.chem_df = chem_df
        self.images_df = images_df
        self.well_df = well_df

        print('✅ Data loaded successfully.')

        return self

    def merge_data(self):
        """
        Clean the data.
        """
        print('Extracting well from picture file name...')
        wells_df = self.images_df.drop(columns=['CellCount']).applymap(lambda x: x.split('/')[-1].split('_')[1])
        wells_df['well'] = wells_df.apply(lambda row: row.unique()[0] if row.nunique()==1 else 0, axis=1)

        print('Extracting photo id from picture file name...')
        photo_number_df = self.images_df.drop(columns=['CellCount',]).applymap(lambda x: x.split('/')[-1].split('_')[2])
        photo_number_df['photo_number'] = photo_number_df.apply(lambda row: row.unique()[0][1] if row.nunique()==1 else float('NaN'), axis=1)

        print('Converting photo path for training...')
        self.images_df['Ph-golgi'] = self.images_df['Ph-golgi'].apply(lambda x: Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Ph_golgi', x.split('/')[-1]))
        self.images_df['Hoechst'] = self.images_df['Hoechst'].apply(lambda x: Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Hoechst', x.split('/')[-1]))
        self.images_df['ERSyto'] = self.images_df['ERSyto'].apply(lambda x: Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSyto', x.split('/')[-1]))
        self.images_df['Mito'] = self.images_df['Mito'].apply(lambda x: Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-Mito', x.split('/')[-1]))
        self.images_df['ERSytoBleed'] = self.images_df['ERSytoBleed'].apply(lambda x: Path(LOCAL_DATA_PATH).joinpath(PLATE_NUMBER, 'Raw_pictures', f'{PLATE_NUMBER}-ERSytoBleed', x.split('/')[-1]))

        print('Concatenating...')
        self.merged_df = pd.concat([
            self.images_df,
            wells_df['well'],
            photo_number_df['photo_number'],
        ],
        axis = 1)

        print('Identifying drugs used per well...')

        chem_cols = ['BROAD_ID', 'CPD_NAME', 'CPD_NAME_TYPE', 'SOURCE_NAME', 'CPD_SMILES']
        well_cols = ['Metadata_Well', 'Metadata_ASSAY_WELL_ROLE', 'Metadata_broad_sample', 'Metadata_mmoles_per_liter',]

        chem_df = self.chem_df[chem_cols].rename(columns={'BROAD_ID':'Drug_id'})
        well_df = self.well_df[well_cols].rename(columns={'Metadata_broad_sample':'Drug_id', 'Metadata_Well':'well'})

        self.merged_df = self.merged_df.merge((well_df.merge(chem_df, how='left')), how='left')

        print('✅ Data Merged')

    def save(self):
        saving_path = Path(LOCAL_DATA_PATH).joinpath(self.plate_number, 'processed', f'{PLATE_NUMBER}_processed.csv')
        self.merged_df.to_csv(saving_path, index=False)
        print(f'✅ Data saved to {saving_path}')


if __name__ == '__main__':
    plate = Plate('24277').load()
    plate.merge_data()
    plate.save()
