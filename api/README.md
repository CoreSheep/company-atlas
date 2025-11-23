# Company Atlas REST API

RESTful API for accessing the unified companies data from the `MARTS.UNIFIED_COMPANIES` table.

## Setup

1. Install dependencies:
```bash
pip install -r ../requirements.txt
```

2. Ensure your `~/.env` file has the required Snowflake credentials:
```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password  # or use private key
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8  # optional, for MFA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=COMPANY_ATLAS
SNOWFLAKE_SCHEMA=MARTS
SNOWFLAKE_ROLE=TRANSFORM
```

## Running the API

### Using the run script:
```bash
./api/run_api.sh
```

### Or directly with uvicorn:
```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /health` - Check API and database connection status

### Companies
- `GET /api/v1/companies` - Search and list companies with filtering and pagination
  - Query parameters:
    - `page` (int): Page number (default: 1)
    - `page_size` (int): Results per page (default: 10, max: 100)
    - `company_name` (string): Filter by company name (partial match)
    - `industry` (string): Filter by industry
    - `country` (string): Filter by country
    - `min_employees` (int): Minimum employee count
    - `max_employees` (int): Maximum employee count
    - `min_revenue` (float): Minimum revenue
    - `max_revenue` (float): Maximum revenue
    - `founded_year` (int): Filter by founded year
    - `source_system` (string): Filter by source system

- `GET /api/v1/companies/{company_id}` - Get a specific company by ID

### Statistics
- `GET /api/v1/statistics` - Get dataset statistics (counts, distributions, averages)

### Reference Data
- `GET /api/v1/industries` - Get list of all industries
- `GET /api/v1/countries` - Get list of all countries

## Example Requests

### Search companies:
```bash
curl "http://localhost:8000/api/v1/companies?country=USA&min_employees=1000&page=1&page_size=10"
```

### Get specific company:
```bash
curl "http://localhost:8000/api/v1/companies/{company_id}"
```

### Get statistics:
```bash
curl "http://localhost:8000/api/v1/statistics"
```

## Response Format

All endpoints return JSON responses. The company search endpoint returns:
```json
{
  "companies": [...],
  "total": 1000,
  "page": 1,
  "page_size": 10
}
```

## Authentication

The API currently doesn't require authentication. For production, consider adding:
- API keys
- OAuth2
- JWT tokens

