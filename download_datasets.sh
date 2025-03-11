#!/bin/bash

# Create datasets directory if it doesn't exist
mkdir -p datasets
cd datasets

# Download datasets using cURL
echo "Downloading stock market historical data..."
curl -L -o top-10-companies.zip \
  "https://www.kaggle.com/api/v1/datasets/download/khushipitroda/stock-market-historical-data-of-top-10-companies"

echo "Downloading NVIDIA/AMD/Intel share prices..."
curl -L -o hardware-companies.zip \
  "https://www.kaggle.com/api/v1/datasets/download/kapturovalexander/nvidia-amd-intel-asus-msi-share-prices"

echo "Downloading NASDAQ companies data..."
curl -L -o nasdaq-companies.zip \
  "https://www.kaggle.com/api/v1/datasets/download/omermetinn/values-of-top-nasdaq-copanies-from-2010-to-2020"

# Unzip all downloaded files
echo "Extracting files..."
for zip in *.zip; do
    unzip -o "$zip"
    rm "$zip"  # Remove zip file after extraction
done

cd ..
echo "Download and extraction complete!" 