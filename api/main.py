"""
FastAPI REST API for Company Atlas data product.
Provides access to unified company dataset via REST endpoints.
"""

import os
import logging
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Company Atlas API",
    description="REST API for accessing unified firmographic company data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class Company(BaseModel):
    """Company data model."""
    company_id: str
    company_name: str
    domain: Optional[str] = None
    ticker: Optional[str] = None
    fortune_rank: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    headquarters_city: Optional[str] = None
    headquarters_state: Optional[str] = None
    ceo: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    revenue: Optional[float] = None
    market_cap_march_m: Optional[float] = None
    market_cap_updated_m: Optional[float] = None
    revenue_percent_change: Optional[float] = None
    profits_m: Optional[float] = None
    profits_percent_change: Optional[float] = None
    assets_m: Optional[float] = None
    source_system: str
    last_updated_at: Optional[str] = None
    mart_created_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "abc123",
                "company_name": "Example Corp",
                "domain": "example.com",
                "ticker": "EXMP",
                "fortune_rank": 500,
                "sector": "Technology",
                "industry": "Software",
                "country": "USA",
                "headquarters_city": "San Francisco",
                "headquarters_state": "CA",
                "ceo": "John Doe",
                "founded_year": 2010,
                "employee_count": 1000,
                "revenue": 50000000.0,
                "source_system": "fortune1000",
                "last_updated_at": "2024-01-01T00:00:00Z"
            }
        }


class CompanySearch(BaseModel):
    """Company search response model."""
    companies: List[Company]
    total: int
    page: int
    page_size: int


class Statistics(BaseModel):
    """Dataset statistics model."""
    total_companies: int
    countries: Dict[str, int]
    industries: Dict[str, int]
    average_employee_count: Optional[float] = None
    average_revenue: Optional[float] = None
    oldest_company_year: Optional[int] = None
    newest_company_year: Optional[int] = None


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    database_connected: bool


# Database connection helper
def get_snowflake_connection():
    """Get Snowflake database connection."""
    try:
        # Support both password and private key authentication
        conn_params = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.getenv("SNOWFLAKE_DATABASE", "COMPANY_ATLAS"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA", "MARTS"),
            "role": os.getenv("SNOWFLAKE_ROLE", "TRANSFORM")
        }
        
        # Use private key if available, otherwise use password
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
        if private_key_path and os.path.exists(private_key_path):
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            with open(private_key_path, "rb") as key_file:
                p_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode() if os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") else None,
                    backend=default_backend()
                )
            
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            conn_params["private_key"] = pkb
        else:
            conn_params["password"] = os.getenv("SNOWFLAKE_PASSWORD")
        
        conn = snowflake.connector.connect(**conn_params)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Snowflake: {e}")
        raise


# API Routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "Company Atlas API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_snowflake_connection()
        conn.close()
        db_connected = True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_connected = False
    
    return HealthCheck(
        status="healthy" if db_connected else "unhealthy",
        version="1.0.0",
        database_connected=db_connected
    )


@app.get("/api/v1/companies", response_model=CompanySearch)
async def get_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of results per page"),
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country: Optional[str] = Query(None, description="Filter by country"),
    min_employees: Optional[int] = Query(None, ge=0, description="Minimum employee count"),
    max_employees: Optional[int] = Query(None, ge=0, description="Maximum employee count"),
    min_revenue: Optional[float] = Query(None, ge=0, description="Minimum revenue"),
    max_revenue: Optional[float] = Query(None, ge=0, description="Maximum revenue"),
    founded_year: Optional[int] = Query(None, description="Filter by founded year"),
    source_system: Optional[str] = Query(None, description="Filter by source system")
):
    """
    Search and retrieve companies with filtering and pagination.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of results per page (max 100)
        company_name: Filter by company name (partial match)
        industry: Filter by industry
        country: Filter by country
        min_employees: Minimum employee count
        max_employees: Maximum employee count
        min_revenue: Minimum revenue
        max_revenue: Maximum revenue
        founded_year: Filter by founded year
        source_system: Filter by source system
        
    Returns:
        Paginated list of companies matching filters
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause with Snowflake parameter binding (?)
        where_conditions = []
        params = []
        
        if company_name:
            where_conditions.append("UPPER(company_name) LIKE UPPER(?)")
            params.append(f"%{company_name}%")
        
        if industry:
            where_conditions.append("industry = ?")
            params.append(industry)
        
        if country:
            where_conditions.append("country = ?")
            params.append(country)
        
        if min_employees is not None:
            where_conditions.append("employee_count >= ?")
            params.append(min_employees)
        
        if max_employees is not None:
            where_conditions.append("employee_count <= ?")
            params.append(max_employees)
        
        if min_revenue is not None:
            where_conditions.append("revenue >= ?")
            params.append(min_revenue)
        
        if max_revenue is not None:
            where_conditions.append("revenue <= ?")
            params.append(max_revenue)
        
        if founded_year:
            where_conditions.append("founded_year = ?")
            params.append(founded_year)
        
        if source_system:
            where_conditions.append("source_system = ?")
            params.append(source_system)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Count total
        count_query = "SELECT COUNT(*) as total FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES WHERE " + where_clause
        
        # Execute count query
        if params:
        cursor.execute(count_query, params)
        else:
            cursor.execute(count_query)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]
        
        query = """SELECT 
                company_id,
                company_name,
                domain,
                ticker,
                fortune_rank,
                sector,
                industry,
                country,
                headquarters_city,
                headquarters_state,
                ceo,
                founded_year,
                employee_count,
                revenue,
                market_cap_march_m,
                market_cap_updated_m,
                revenue_percent_change,
                profits_m,
                profits_percent_change,
                assets_m,
                source_system,
                last_updated_at,
                mart_created_at
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE """ + where_clause + """
            ORDER BY company_name
            LIMIT ?
            OFFSET ?"""
        
        # Execute query
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        # Convert to Company models
        companies = []
        for row in rows:
            company = Company(
                company_id=row[0],
                company_name=row[1],
                domain=row[2],
                ticker=row[3],
                fortune_rank=row[4],
                sector=row[5],
                industry=row[6],
                country=row[7],
                headquarters_city=row[8],
                headquarters_state=row[9],
                ceo=row[10],
                founded_year=row[11],
                employee_count=row[12],
                revenue=row[13],
                market_cap_march_m=row[14],
                market_cap_updated_m=row[15],
                revenue_percent_change=row[16],
                profits_m=row[17],
                profits_percent_change=row[18],
                assets_m=row[19],
                source_system=row[20],
                last_updated_at=str(row[21]) if row[21] else None,
                mart_created_at=str(row[22]) if row[22] else None
            )
            companies.append(company)
        
        cursor.close()
        conn.close()
        
        return CompanySearch(
            companies=companies,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/companies/{company_id}", response_model=Company)
async def get_company(company_id: str):
    """
    Get a specific company by ID.
    
    Args:
        company_id: Company identifier
        
    Returns:
        Company details
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                company_id,
                company_name,
                domain,
                ticker,
                fortune_rank,
                sector,
                industry,
                country,
                headquarters_city,
                headquarters_state,
                ceo,
                founded_year,
                employee_count,
                revenue,
                market_cap_march_m,
                market_cap_updated_m,
                revenue_percent_change,
                profits_m,
                profits_percent_change,
                assets_m,
                source_system,
                last_updated_at,
                mart_created_at
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE company_id = ?
        """
        
        cursor.execute(query, (company_id,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        
        company = Company(
            company_id=row[0],
            company_name=row[1],
            domain=row[2],
            ticker=row[3],
            fortune_rank=row[4],
            sector=row[5],
            industry=row[6],
            country=row[7],
            headquarters_city=row[8],
            headquarters_state=row[9],
            ceo=row[10],
            founded_year=row[11],
            employee_count=row[12],
            revenue=row[13],
            market_cap_march_m=row[14],
            market_cap_updated_m=row[15],
            revenue_percent_change=row[16],
            profits_m=row[17],
            profits_percent_change=row[18],
            assets_m=row[19],
            source_system=row[20],
            last_updated_at=str(row[21]) if row[21] else None,
            mart_created_at=str(row[22]) if row[22] else None
        )
        
        return company
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving company: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/statistics", response_model=Statistics)
async def get_statistics():
    """
    Get dataset statistics.
    
    Returns:
        Dataset statistics including counts, distributions, and aggregations
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        # Total companies
        cursor.execute("SELECT COUNT(*) FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES")
        total_companies = cursor.fetchone()[0]
        
        # Country distribution
        cursor.execute("""
            SELECT country, COUNT(*) as count
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY count DESC
            LIMIT 20
        """)
        countries = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Industry distribution
        cursor.execute("""
            SELECT industry, COUNT(*) as count
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE industry IS NOT NULL
            GROUP BY industry
            ORDER BY count DESC
            LIMIT 20
        """)
        industries = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Averages
        cursor.execute("""
            SELECT 
                AVG(employee_count) as avg_employees,
                AVG(revenue) as avg_revenue,
                MIN(founded_year) as oldest_year,
                MAX(founded_year) as newest_year
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE employee_count IS NOT NULL
               OR revenue IS NOT NULL
               OR founded_year IS NOT NULL
        """)
        row = cursor.fetchone()
        avg_employees = row[0] if row[0] else None
        avg_revenue = row[1] if row[1] else None
        oldest_year = row[2] if row[2] else None
        newest_year = row[3] if row[3] else None
        
        cursor.close()
        conn.close()
        
        return Statistics(
            total_companies=total_companies,
            countries=countries,
            industries=industries,
            average_employee_count=float(avg_employees) if avg_employees else None,
            average_revenue=float(avg_revenue) if avg_revenue else None,
            oldest_company_year=oldest_year,
            newest_company_year=newest_year
        )
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/industries", response_model=List[str])
async def get_industries():
    """
    Get list of all industries.
    
    Returns:
        List of unique industries
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT industry
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE industry IS NOT NULL
            ORDER BY industry
        """)
        
        industries = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return industries
        
    except Exception as e:
        logger.error(f"Error retrieving industries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/countries", response_model=List[str])
async def get_countries():
    """
    Get list of all countries.
    
    Returns:
        List of unique countries
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT country
            FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
            WHERE country IS NOT NULL
            ORDER BY country
        """)
        
        countries = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return countries
        
    except Exception as e:
        logger.error(f"Error retrieving countries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

