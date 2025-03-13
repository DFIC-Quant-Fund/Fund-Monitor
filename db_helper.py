import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_engine(db_name):
    connection_string = (
        f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{db_name}"
    )
    engine = create_engine(connection_string)
    return engine

def query_data(db_name, query, params=None):
    engine = get_db_engine(db_name)
    df = pd.read_sql(query, engine, params=params)
    engine.dispose()
    return df

def store_dataframe(db_name, df, table_name, if_exists='replace'):
    engine = get_db_engine(db_name)
    
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)
    
    if if_exists == 'replace':
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        mode = 'append'
    else:
        mode = if_exists
    
    df.to_sql(name=table_name, con=engine, if_exists=mode, index=False)
    engine.dispose()
