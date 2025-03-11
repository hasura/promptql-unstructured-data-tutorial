import os
import glob
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_values
import psycopg2.extensions
from openai import OpenAI
from tqdm import tqdm
import numpy as np
from datetime import datetime
import time

# Constants
CHUNK_SIZE = 1000  # characters per chunk
OVERLAP = 200  # character overlap between chunks
BATCH_SIZE = 100  # number of chunks to process at once
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Register numpy array adapter for PostgreSQL
def adapt_numpy_array(numpy_array):
    return psycopg2.extensions.AsIs(str(numpy_array.tolist()))

psycopg2.extensions.register_adapter(np.ndarray, adapt_numpy_array)

def get_db_connection():
    """Create a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host="local.hasura.dev",
        port=7861,
        database="dev",
        user="user",
        password="password"
    )

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        # If this is not the first chunk, include the overlap from the previous chunk
        if start > 0:
            start = start - overlap
        chunk = text[start:end]
        chunks.append(chunk)
        start = end
    
    return chunks

def extract_stock_and_date(filepath: str) -> Tuple[str, str]:
    """Extract stock symbol and date from filepath.
    
    Example:
    datasets/Transcripts/MU/2020-Jun-29-MU.txt -> ('MU', '2020-06-29')
    """
    # Get stock symbol from parent directory name
    stock_symbol = os.path.basename(os.path.dirname(filepath))
    
    # Extract date from filename
    filename = os.path.basename(filepath)
    date_str = filename.split('-', 3)[:3]  # Get first 3 parts: ['2020', 'Jun', '29']
    
    # Convert month abbreviation to number
    date_obj = datetime.strptime('-'.join(date_str), '%Y-%b-%d')
    formatted_date = date_obj.strftime('%Y-%m-%d')
    
    return stock_symbol, formatted_date

def get_embeddings_with_retry(client: OpenAI, batch: List[str], retries: int = MAX_RETRIES) -> List[List[float]]:
    """Get embeddings with retry logic for API calls."""
    for attempt in range(retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            if attempt == retries - 1:  # Last attempt
                raise e
            print(f"Embedding API error (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff

def process_transcript(filepath: str, client: OpenAI, cursor) -> None:
    """Process a single transcript file."""
    # Read the transcript
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract metadata
    stock_symbol, date = extract_stock_and_date(filepath)
    
    # Check if transcript already exists
    cursor.execute(
        "SELECT id FROM transcripts WHERE stock_symbol = %s AND date = %s",
        (stock_symbol, date)
    )
    existing = cursor.fetchone()
    if existing:
        print(f"Skipping {filepath} - already processed")
        return
    
    # Insert transcript
    cursor.execute(
        """
        INSERT INTO transcripts (stock_symbol, date, content)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (stock_symbol, date, content)
    )
    transcript_id = cursor.fetchone()[0]
    
    # Chunk the content
    chunks = chunk_text(content)
    
    # Process chunks in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        
        # Get embeddings for the batch with retry logic
        embeddings = get_embeddings_with_retry(client, batch)
        
        # Prepare data for bulk insert
        values = [
            (transcript_id, chunk, embedding)
            for chunk, embedding in zip(batch, embeddings)
        ]
        
        # Bulk insert vectors
        execute_values(
            cursor,
            """
            INSERT INTO transcript_vectors (transcript_id, content_chunk, content_chunk_vector)
            VALUES %s
            """,
            values,
            template="(%s, %s, %s)"
        )

def main():
    # Initialize OpenAI client
    client = OpenAI()
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    # Get all transcript files from all company folders
    transcript_files = []
    company_folders = glob.glob("datasets/Transcripts/*/")
    for folder in company_folders:
        transcript_files.extend(glob.glob(os.path.join(folder, "*.txt")))
    
    print(f"Found {len(transcript_files)} transcript files")
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Process each transcript
        for filepath in tqdm(transcript_files, desc="Processing transcripts"):
            try:
                process_transcript(filepath, client, cursor)
                conn.commit()
                print(f"Successfully processed: {filepath}")
            except Exception as e:
                print(f"Error processing {filepath}: {str(e)}")
                conn.rollback()
                time.sleep(1)  # Small delay before next file
    
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Rolling back current transaction...")
        conn.rollback()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main() 