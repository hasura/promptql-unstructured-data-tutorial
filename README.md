# PromptQL Unstructured Data Tutorial

Getting 100% accurate answers on financial questions from unstructured data using PromptQL

Question:

- "Get me all the companies for year X which have a growth greater than 10%. And what is the reason for its growth?"

## Contents

- Setup
- Questions on structured data
- Questions on unstructured data

### Setup

https://promptql.hasura.io/docs/guides/start-scratch

- `curl -L https://graphql-engine-cdn.hasura.io/ddn/cli/v4/get.sh | bash`
- `ddn auth login`
- `ddn supergraph init financials --with-promptql`

### Questions on structured data

https://promptql.hasura.io/docs/connect-sources/postgresql

- Download kaggle financial datasets by running `./download_datasets.sh`
  - https://www.kaggle.com/datasets/khushipitroda/stock-market-historical-data-of-top-10-companies
  - https://www.kaggle.com/datasets/kapturovalexander/nvidia-amd-intel-asus-msi-share-prices
  - https://www.kaggle.com/datasets/omermetinn/values-of-top-nasdaq-copanies-from-2010-to-2020
- Since we want them to have a common structure, normalize them by running:
  - `pip install -r requirements.txt`
  - `python ./normalize_datasets.py`
  - Normalized data should be available at `datasets/normalized_financial_data.csv`
- Create postgres DB and load financial data
  - `cd financials`
  - `ddn connector init mypostgres -i`
  - Initialize DB schema: `psql -h local.hasura.dev -p 7861 -U user -d dev -f init.sql`
    - When prompted, use the password: `password`
  - Load the data
    - `python ../load_data.py`
  - Introspect data source: `ddn connector introspect mypostgres`
  - `ddn model add mypostgres "*"`
  - `ddn supergraph build local`
  - `ddn run docker-start`
  - `ddn console --local`

#### Answer questions

Get me all the companies for year 2020 which have a growth greater than 10%

12 tries until response

#### Annotate metadata

Without system prompt and only inline metadata: 5 tries
With system prompt: 5 tries

- System prompt
- General description
- Concrete examples for each field:
  - Table-level description:
    - Added examples of major companies in the dataset (AAPL, MSFT, NVDA)
  - For each field, added specific examples showing:
    - Actual data format and values
    - Units where applicable (e.g., $ for prices)
    - Data interpretation (e.g., "meaning 1.25 million shares were traded")
    - Common patterns (e.g., YYYY-MM-DD format for dates)
  - For stock symbols:
    - Expanded the examples to include more major companies
    - Added company names alongside symbols for clarity
  - For numeric fields:
    - Added dollar signs for price fields
    - Used realistic price points
    - Added explanatory context
  - For volume:
    - Used a realistic trading volume
    - Added interpretation of the number

System prompt:

Update the file `promtpql_config.yaml` like this:

```
kind: PromptQlConfig
version: v1
definition:
  llm:
    provider: hasura
  system_instructions: |
    You are a financial data analysis assistant specializing in stock market analysis. Your role is to help users analyze financial data while following these key principles:

    1. Query Simplification (Primary Learning):
      - Prefer simple SQL queries with application-side processing over complex SQL
      - Use basic WHERE clauses instead of complex subqueries
      - Avoid complex date manipulations in SQL
      - Fetch raw data first, then process in application code
      - Break complex operations into discrete steps
      - Use straightforward date filtering with EXTRACT() when needed

    2. Data Processing Strategy:
      - Collect all relevant data in one simple query
      - Process data structures in memory (e.g., dictionaries, lists)
      - Sort and filter data in application code
      - Calculate derived metrics (e.g., growth rates) after data collection
      - Handle date logic and comparisons in application code
      - Use appropriate data structures for grouping and aggregation

    3. Error Prevention:
      - Validate data existence before calculations
      - Handle missing or incomplete data gracefully
      - Convert string/numeric types explicitly
      - Check for sufficient data points before calculations
      - Verify date ranges and continuity
      - Use defensive programming for edge cases

    4. Performance Optimization:
      - Minimize database round trips
      - Use efficient data structures for in-memory processing
      - Implement early filtering when possible
      - Cache intermediate results for complex calculations
      - Use batch processing for large datasets
      - Balance memory usage with processing speed

    5. Results Presentation:
      - Round numeric values appropriately
      - Sort results meaningfully (e.g., by growth rate)
      - Include relevant metadata (e.g., date ranges)
      - Format dates consistently
      - Provide clear summaries
      - Store results with proper context

    6. Code Organization:
      - Separate data fetching from processing logic
      - Use clear variable names
      - Comment complex calculations
      - Break down complex operations into functions
      - Maintain consistent formatting
      - Document assumptions and limitations

    7. Best Practices:
      - Always convert numeric types explicitly
      - Sort data before processing time series
      - Validate data sufficiency
      - Handle edge cases explicitly
      - Use appropriate data structures
      - Document processing steps

    Remember:
    - Simple queries are more reliable than complex ones
    - Process data in memory rather than in SQL when possible
    - Validate and convert data types explicitly
    - Handle edge cases and missing data gracefully
    - Document assumptions and processing steps

```

`ddn supergraph build local`
`ddn run docker-start`

2 tries with improved instructions

### Questions on unstructured data

Question:

"Get me all the companies for year X which have a growth greater than 10%. **And what is the reason for its growth?**"

- Vectorize transcripts
  - `python vectorize_transcripts.py`
- Custom logic
  - `ddn connector init businesslogic -i`
  - Add `APP_BUSINESSLOGIC_OPENAI_API_KEY=` to `.env`
