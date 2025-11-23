"""
Fortune 1000 dataset ingestion with web scraping enrichment.
Uses the Fortune 1000 dataset as primary source and enriches missing fields via web scraping.
"""

import os
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import kaggle
from dotenv import load_dotenv
import trio
from .web_scraper import WebScraper, enrich_company_dataframe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Fortune1000Ingestion:
    """Handles Fortune 1000 dataset ingestion with web scraping enrichment."""
    
    def __init__(self, output_dir: str = "data/raw", enrich_with_scraping: bool = True):
        """
        Initialize Fortune 1000 ingestion.
        
        Args:
            output_dir: Directory to save downloaded data
            enrich_with_scraping: Whether to enrich data with web scraping
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enrich_with_scraping = enrich_with_scraping
        
        # Configure Kaggle API
        kaggle.api.authenticate()
        
        # Initialize web scraper if needed
        self.scraper = WebScraper() if enrich_with_scraping else None
    
    def download_fortune1000(self) -> pd.DataFrame:
        """
        Download Fortune 1000 dataset from Kaggle.
        
        Returns:
            DataFrame with Fortune 1000 company data
        """
        logger.info("Downloading Fortune 1000 dataset...")
        
        dataset = "jeannicolasduval/2024-fortune-1000-companies"
        local_path = self.output_dir / "fortune1000"
        local_path.mkdir(exist_ok=True)
        
        try:
            kaggle.api.dataset_download_files(
                dataset,
                path=str(local_path),
                unzip=True,
                quiet=False
            )
            
            # Find CSV or Parquet files
            csv_files = list(local_path.glob("*.csv"))
            parquet_files = list(local_path.glob("*.parquet"))
            
            if csv_files:
                # Read CSV file (prefer the main file)
                main_csv = csv_files[0] if len(csv_files) == 1 else \
                    next((f for f in csv_files if 'fortune' in f.name.lower() and '2024' in f.name), csv_files[0])
                df = pd.read_csv(main_csv)
                logger.info(f"Downloaded {len(df)} records from Fortune 1000 dataset")
                logger.info(f"Columns: {list(df.columns)}")
                return df
            elif parquet_files:
                # Read parquet file (use the main one if multiple)
                main_file = parquet_files[0] if len(parquet_files) == 1 else \
                    next((f for f in parquet_files if 'companyinfo' in f.name or 'companies' in f.name), parquet_files[0])
                df = pd.read_parquet(main_file)
                logger.info(f"Downloaded {len(df)} records from Fortune 1000 dataset")
                logger.info(f"Columns: {list(df.columns)}")
                return df
            else:
                raise FileNotFoundError("No CSV or Parquet files found in downloaded dataset")
                
        except Exception as e:
            logger.error(f"Error downloading Fortune 1000 dataset: {e}")
            raise
    
    def normalize_schema(self, df: pd.DataFrame, source_system: str = "fortune1000") -> pd.DataFrame:
        """
        Normalize Fortune 1000 dataset to unified schema.
        
        Args:
            df: Input DataFrame
            source_system: Source system identifier
            
        Returns:
            Normalized DataFrame with unified schema
        """
        logger.info(f"Normalizing schema for {source_system}...")
        
        df_normalized = df.copy()
        
        # Common column name mappings for Fortune 1000 dataset
        column_mapping = {
            "name": "company_name",
            "company": "company_name",
            "company_name": "company_name",
            "website": "domain",
            "url": "domain",
            "domain": "domain",
            "industry": "industry",
            "sector": "industry",
            "industry_type": "industry",
            "country": "country",
            "country_code": "country",
            "location": "country",
            "employees": "employee_count",
            "employee_count": "employee_count",
            "num_employees": "employee_count",
            "revenue": "revenue",
            "revenues": "revenue",
            "annual_revenue": "revenue",
            "founded": "founded_year",
            "founded_year": "founded_year",
            "year_founded": "founded_year",
            "established": "founded_year",
        }
        
        # Rename columns (case-insensitive)
        rename_dict = {}
        for col in df_normalized.columns:
            col_lower = col.lower().strip()
            if col_lower in column_mapping:
                rename_dict[col] = column_mapping[col_lower]
        
        df_normalized = df_normalized.rename(columns=rename_dict)
        
        # Ensure required columns exist (create empty if missing)
        required_columns = [
            "company_name",
            "domain",
            "industry",
            "country",
            "employee_count",
            "revenue",
            "founded_year"
        ]
        
        for col in required_columns:
            if col not in df_normalized.columns:
                df_normalized[col] = None
        
        # Clean and normalize data
        if 'company_name' in df_normalized.columns:
            df_normalized['company_name'] = df_normalized['company_name'].astype(str).str.strip()
        
        if 'domain' in df_normalized.columns:
            # Clean domain (remove http://, https://, www.)
            df_normalized['domain'] = df_normalized['domain'].astype(str).str.lower().str.strip()
            df_normalized['domain'] = df_normalized['domain'].str.replace(r'^https?://', '', regex=True)
            df_normalized['domain'] = df_normalized['domain'].str.replace(r'^www\.', '', regex=True)
            df_normalized['domain'] = df_normalized['domain'].str.split('/').str[0]
        
        if 'country' in df_normalized.columns:
            df_normalized['country'] = df_normalized['country'].astype(str).str.upper().str.strip()
            # Normalize country names
            df_normalized['country'] = df_normalized['country'].replace({
                'US': 'USA',
                'UNITED STATES': 'USA',
                'UNITED STATES OF AMERICA': 'USA',
                'UK': 'UK',
                'UNITED KINGDOM': 'UK',
            })
        
        # Convert numeric columns
        if 'employee_count' in df_normalized.columns:
            df_normalized['employee_count'] = pd.to_numeric(df_normalized['employee_count'], errors='coerce')
        
        if 'revenue' in df_normalized.columns:
            df_normalized['revenue'] = pd.to_numeric(df_normalized['revenue'], errors='coerce')
        
        if 'founded_year' in df_normalized.columns:
            df_normalized['founded_year'] = pd.to_numeric(df_normalized['founded_year'], errors='coerce')
        
        # Add metadata columns
        df_normalized["source_system"] = source_system
        df_normalized["last_updated_at"] = datetime.utcnow().isoformat()
        
        # Select and order columns
        final_columns = required_columns + ["source_system", "last_updated_at"]
        df_normalized = df_normalized[[col for col in final_columns if col in df_normalized.columns]]
        
        logger.info(f"Normalized {len(df_normalized)} records")
        return df_normalized
    
    async def enrich_with_scraping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich DataFrame with web-scraped data for missing fields.
        
        Args:
            df: DataFrame with company data
            
        Returns:
            Enriched DataFrame
        """
        if not self.enrich_with_scraping or not self.scraper:
            return df
        
        logger.info("Enriching data with web scraping...")
        
        # Identify companies with missing critical fields
        missing_fields = df.isnull() | (df == '') | (df == 'None')
        
        # Priority: enrich companies missing domain, industry, employee_count, founded_year
        needs_enrichment = (
            missing_fields['domain'] | 
            missing_fields['industry'] | 
            missing_fields['employee_count'] | 
            missing_fields['founded_year']
        )
        
        companies_to_enrich = df[needs_enrichment].copy()
        companies_enriched = df[~needs_enrichment].copy()
        
        if len(companies_to_enrich) == 0:
            logger.info("No companies need enrichment")
            return df
        
        logger.info(f"Enriching {len(companies_to_enrich)} companies with missing data...")
        
        # Enrich companies
        enriched_list = await self.scraper.enrich_companies_async(
            companies_to_enrich.to_dict('records')
        )
        enriched_df = pd.DataFrame(enriched_list)
        
        # Combine enriched and already complete companies
        final_df = pd.concat([companies_enriched, enriched_df], ignore_index=True)
        
        logger.info(f"Successfully enriched {len(enriched_df)} companies")
        return final_df
    
    async def ingest_all(self) -> pd.DataFrame:
        """
        Ingest Fortune 1000 dataset and enrich with web scraping.
        
        Returns:
            Enriched and normalized DataFrame
        """
        try:
            # Download dataset (synchronous operation)
            df = self.download_fortune1000()
            
            # Normalize schema
            df_normalized = self.normalize_schema(df)
            
            # Enrich with web scraping (async operation)
            if self.enrich_with_scraping:
                df_enriched = await self.enrich_with_scraping(df_normalized)
            else:
                df_enriched = df_normalized
            
            return df_enriched
            
        except Exception as e:
            logger.error(f"Failed to ingest Fortune 1000 dataset: {e}")
            raise
        finally:
            # Close scraper
            if self.scraper:
                await self.scraper.close()


async def main():
    """Main function to run ingestion."""
    ingester = Fortune1000Ingestion(enrich_with_scraping=True)
    df = await ingester.ingest_all()
    print(f"\nIngested {len(df)} companies")
    print(f"\nMissing data summary:")
    print(df.isnull().sum())
    return df


if __name__ == "__main__":
    df = trio.run(main)
    print(f"\nSample data:")
    print(df.head())

