-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the financial_data table
CREATE TABLE IF NOT EXISTS financial_data (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    stock_symbol VARCHAR(10) NOT NULL,
    open_price DECIMAL(12, 4) NOT NULL,
    high_price DECIMAL(12, 4) NOT NULL,
    low_price DECIMAL(12, 4) NOT NULL,
    close_price DECIMAL(12, 4) NOT NULL,
    volume DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_financial_data_date ON financial_data(date);
CREATE INDEX IF NOT EXISTS idx_financial_data_stock_symbol ON financial_data(stock_symbol);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_financial_data_stock_date ON financial_data(stock_symbol, date);

-- Create table for storing transcripts
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    stock_symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create table for storing transcript vectors
CREATE TABLE IF NOT EXISTS transcript_vectors (
    id SERIAL PRIMARY KEY,
    transcript_id INTEGER REFERENCES transcripts(id),
    content_chunk TEXT NOT NULL,
    content_chunk_vector vector(1536), -- OpenAI's text-embedding-3-small dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for transcript tables
CREATE INDEX IF NOT EXISTS idx_transcripts_stock_date ON transcripts(stock_symbol, date);
CREATE INDEX IF NOT EXISTS idx_transcript_vectors_transcript_id ON transcript_vectors(transcript_id);

-- Create vector similarity search index
CREATE INDEX IF NOT EXISTS idx_transcript_vectors_vector ON transcript_vectors USING ivfflat (content_chunk_vector vector_cosine_ops); 