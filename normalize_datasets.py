import pandas as pd
import os
from datetime import datetime

def normalize_date(date_str):
    """Convert various date formats to YYYY-MM-DD."""
    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except:
        return None

def process_hardware_companies():
    """Process files from hardware-companies.zip"""
    dfs = []
    
    # Map of filename patterns to stock symbols
    symbol_map = {
        'AMD': 'AMD',
        'INTEL': 'INTC',
        'NVIDIA': 'NVDA',
        'ASUS': 'ASUS',
        'MSI': 'MSI'
    }
    
    for file in os.listdir('datasets'):
        if file.endswith('.csv'):
            for company in symbol_map:
                if company in file.upper():
                    try:
                        df = pd.read_csv(f'datasets/{file}')
                        print(f"Columns in {file}: {df.columns.tolist()}")
                        
                        df['stockSymbol'] = symbol_map[company]
                        
                        # Handle Close column
                        if 'Close' in df.columns:
                            df = df.drop('Adj Close', axis=1, errors='ignore')
                        elif 'Adj Close' in df.columns:
                            df['Close'] = df['Adj Close']
                            df = df.drop('Adj Close', axis=1)
                        
                        # Remove any remaining duplicate columns
                        df = df.loc[:,~df.columns.duplicated()]
                        dfs.append(df)
                    except Exception as e:
                        print(f"Error processing {file}: {e}")
    
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        return combined
    return pd.DataFrame()

def process_nasdaq_companies():
    """Process files from nasdaq-companies.zip"""
    try:
        companies = pd.read_csv('datasets/Company.csv')
        values = pd.read_csv('datasets/CompanyValues.csv')
        print(f"NASDAQ values columns: {values.columns.tolist()}")
        
        merged = values.merge(companies, on='ticker_symbol', how='left')
        
        merged = merged.rename(columns={
            'ticker_symbol': 'stockSymbol',
            'day_date': 'Date',
            'close_value': 'Close',
            'volume': 'Volume',
            'open_value': 'Open',
            'high_value': 'High',
            'low_value': 'Low'
        })
        return merged
    except Exception as e:
        print(f"Error processing NASDAQ data: {e}")
        return pd.DataFrame()

def process_top_10_companies():
    """Process data.csv from top-10-companies.zip"""
    try:
        df = pd.read_csv('datasets/data.csv')
        print(f"Top 10 columns: {df.columns.tolist()}")
        
        # Map company names to stock symbols
        company_to_symbol = {
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT',
            'AMAZON': 'AMZN',
            'CISCO': 'CSCO',
            'MICRON': 'MU'
        }
        
        # Convert company names to uppercase for matching
        df['Company'] = df['Company'].str.upper()
        df['stockSymbol'] = df['Company'].map(company_to_symbol)
        
        # Rename Close/Last to Close
        df = df.rename(columns={'Close/Last': 'Close'})
        
        return df
    except Exception as e:
        print(f"Error processing top 10 companies data: {e}")
        return pd.DataFrame()

def main():
    # Process all datasets
    hardware_df = process_hardware_companies()
    nasdaq_df = process_nasdaq_companies()
    top10_df = process_top_10_companies()
    
    # List of required columns in final output
    required_columns = ['Date', 'stockSymbol', 'Open', 'High', 'Low', 'Close', 'Volume']
    
    # Normalize each dataframe
    dfs = []
    
    for df, name in [(hardware_df, 'hardware'), (nasdaq_df, 'nasdaq'), (top10_df, 'top10')]:
        if not df.empty:
            print(f"\nProcessing {name} dataset")
            print(f"Available columns: {df.columns.tolist()}")
            
            # Check if all required columns exist
            missing_cols = set(required_columns) - set(df.columns)
            if missing_cols:
                print(f"Warning: {name} dataset is missing columns: {missing_cols}")
                continue
            
            try:
                # Select only the required columns and remove duplicates
                df = df[required_columns].copy()
                df = df.drop_duplicates()
                dfs.append(df)
            except Exception as e:
                print(f"Error processing {name} dataset: {e}")
    
    # Combine all dataframes
    if dfs:
        try:
            final_df = pd.concat(dfs, ignore_index=True)
            
            # Normalize data types
            final_df['Date'] = final_df['Date'].apply(normalize_date)
            
            # Clean up numeric columns
            numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in numeric_columns:
                # Remove any currency symbols or commas
                if final_df[col].dtype == 'object':
                    final_df[col] = final_df[col].astype(str).str.replace('$', '').str.replace(',', '')
                final_df[col] = pd.to_numeric(final_df[col], errors='coerce')
            
            # Remove rows with missing values
            final_df = final_df.dropna()
            
            # Sort by date and stock symbol
            final_df = final_df.sort_values(['stockSymbol', 'Date'])
            
            # Save to CSV
            final_df.to_csv('datasets/normalized_financial_data.csv', index=False)
            print(f"\nSuccessfully normalized {len(final_df)} rows of data")
        except Exception as e:
            print(f"\nError in final processing: {e}")
    else:
        print("\nNo data was processed successfully")

if __name__ == "__main__":
    main() 