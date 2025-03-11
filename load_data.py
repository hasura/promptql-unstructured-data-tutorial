import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from datetime import datetime

def load_data():
    # Database connection parameters
    db_params = {
        'host': 'local.hasura.dev',
        'database': 'dev',
        'user': 'user',
        'password': 'password',
        'port': 7861
    }

    try:
        # Read the CSV file
        print("Reading CSV file...")
        df = pd.read_csv('datasets/normalized_financial_data.csv')
        
        # Rename columns to match database schema
        df.columns = ['date', 'stock_symbol', 'open_price', 'high_price', 
                     'low_price', 'close_price', 'volume']
        
        # Convert date string to datetime
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Create SQLAlchemy engine
        engine = create_engine(f'postgresql://{db_params["user"]}:{db_params["password"]}@{db_params["host"]}:{db_params["port"]}/{db_params["database"]}')
        
        # Load data into PostgreSQL
        print("Loading data into PostgreSQL...")
        df.to_sql('financial_data', engine, if_exists='append', index=False,
                  method='multi', chunksize=1000)
        
        print("Data loaded successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    load_data() 