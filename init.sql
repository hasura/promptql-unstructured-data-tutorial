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