"""
Script to download unified_companies data from Snowflake to local JSON file
for website visualization.
"""

import logging
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector
import pandas as pd

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_snowflake_connection():
    """Get Snowflake connection."""
    try:
        # Try private key authentication first
        private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH', '')
        if private_key_path and os.path.exists(private_key_path):
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            with open(private_key_path, 'rb') as key_file:
                p_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE', '').encode() if os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE') else None,
                    backend=default_backend()
                )
            
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            conn = snowflake.connector.connect(
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                user=os.getenv('SNOWFLAKE_USER'),
                private_key=pkb,
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database='COMPANY_ATLAS',
                schema='MARTS',
                role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
            )
        else:
            # Fall back to password authentication
            conn = snowflake.connector.connect(
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                user=os.getenv('SNOWFLAKE_USER'),
                password=os.getenv('SNOWFLAKE_PASSWORD'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database='COMPANY_ATLAS',
                schema='MARTS',
                role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
            )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Snowflake: {e}")
        raise


def download_unified_companies():
    """Download unified_companies data from Snowflake to local JSON file."""
    
    logger.info("Connecting to Snowflake...")
    conn = get_snowflake_connection()
    logger.info("Connected successfully!")
    
    try:
        cursor = conn.cursor()
        
        # Query unified_companies table
        query = """
        SELECT 
            company_id,
            company_name,
            ticker,
            fortune_rank,
            domain,
            industry,
            industry_primary,
            country,
            headquarters_city,
            headquarters_state,
            ceo,
            website,
            founded_year,
            employee_count,
            revenue,
            market_cap_updated_m,
            revenue_percent_change,
            profits_m,
            profits_percent_change,
            assets_m,
            source_system,
            last_updated_at
        FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES
        ORDER BY company_name
        """
        
        logger.info("Querying unified_companies table...")
        cursor.execute(query)
        
        # Fetch all results
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        logger.info(f"Fetched {len(rows)} companies")
        
        # Convert to list of dictionaries with lowercase keys
        companies = []
        for row in rows:
            company = {}
            for col, val in zip(columns, row):
                # Convert to lowercase key
                key = col.lower()
                # Convert datetime to string for JSON serialization
                if key == 'last_updated_at' and val:
                    company[key] = val.isoformat() if hasattr(val, 'isoformat') else str(val)
                else:
                    company[key] = val
            companies.append(company)
        
        # Create output directory
        output_dir = Path('data/marts')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        output_file = output_dir / 'unified_companies.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {len(companies)} companies to {output_file}")
        
        # Calculate statistics
        countries_set = set()
        industries_set = set()
        employee_counts = []
        countries_dist = {}
        industries_dist = {}
        
        for c in companies:
            # Countries
            country = c.get('country')
            if country and str(country).strip() and str(country).upper() != 'UNKNOWN':
                countries_set.add(str(country).strip())
                countries_dist[str(country).strip()] = countries_dist.get(str(country).strip(), 0) + 1
            
            # Industries
            industry = c.get('industry') or c.get('industry_primary')
            if industry and str(industry).strip() and str(industry).upper() != 'UNKNOWN':
                industries_set.add(str(industry).strip())
                industries_dist[str(industry).strip()] = industries_dist.get(str(industry).strip(), 0) + 1
            
            # Employee counts
            emp_count = c.get('employee_count')
            if emp_count and emp_count > 0:
                employee_counts.append(emp_count)
        
        # Sort distributions by count (descending)
        countries_dist_sorted = dict(sorted(countries_dist.items(), key=lambda x: x[1], reverse=True))
        industries_dist_sorted = dict(sorted(industries_dist.items(), key=lambda x: x[1], reverse=True))
        
        stats = {
            'total_companies': len(companies),
            'total_countries': len(countries_set),
            'total_industries': len(industries_set),
            'companies_with_fortune_rank': len([c for c in companies if c.get('fortune_rank')]),
            'companies_with_founded_year': len([c for c in companies if c.get('founded_year')]),
            'companies_with_revenue': len([c for c in companies if c.get('revenue')]),
            'avg_employee_count': sum(employee_counts) / len(employee_counts) if employee_counts else 0,
            'countries': countries_dist_sorted,
            'industries': industries_dist_sorted
        }
        
        stats_file = output_dir / 'statistics.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Saved statistics to {stats_file}")
        logger.info(f"\nStatistics:")
        logger.info(f"  Total companies: {stats['total_companies']}")
        logger.info(f"  Total countries: {stats['total_countries']}")
        logger.info(f"  Total industries: {stats['total_industries']}")
        logger.info(f"  Companies with Fortune rank: {stats['companies_with_fortune_rank']}")
        logger.info(f"  Companies with founded year: {stats['companies_with_founded_year']}")
        
        cursor.close()
        conn.close()
        logger.info("\n✅ Download completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Failed to download data: {e}", exc_info=True)
        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    download_unified_companies()

