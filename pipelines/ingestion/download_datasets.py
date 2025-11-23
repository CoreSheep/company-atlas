"""
Download Fortune 1000 and Global Companies datasets as CSV files.
"""

import logging
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import kaggle
from dotenv import load_dotenv
import trio
from pipelines.ingestion.web_scraper import WebScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_fortune1000(output_dir: Path) -> pd.DataFrame:
    """Download Fortune 1000 dataset."""
    logger.info("="*60)
    logger.info("Downloading Fortune 1000 dataset (Primary)")
    logger.info("="*60)
    
    # Authenticate Kaggle
    kaggle.api.authenticate()
    
    dataset = "jeannicolasduval/2024-fortune-1000-companies"
    local_path = output_dir / "fortune1000"
    local_path.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"Dataset: {dataset}")
    logger.info(f"Downloading to: {local_path}")
    
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
            main_csv = csv_files[0] if len(csv_files) == 1 else \
                next((f for f in csv_files if 'fortune' in f.name.lower() and '2024' in f.name), csv_files[0])
            df = pd.read_csv(main_csv)
            logger.info(f"Downloaded {len(df)} records from CSV")
        elif parquet_files:
            main_file = parquet_files[0] if len(parquet_files) == 1 else \
                next((f for f in parquet_files if 'companyinfo' in f.name or 'companies' in f.name), parquet_files[0])
            df = pd.read_parquet(main_file)
            logger.info(f"Downloaded {len(df)} records from Parquet")
        else:
            raise FileNotFoundError("No CSV or Parquet files found")
        
        logger.info(f"Columns: {list(df.columns)}")
        return df
        
    except Exception as e:
        logger.error(f"Error downloading Fortune 1000: {e}")
        raise


def download_global_companies(output_dir: Path) -> pd.DataFrame:
    """Download Global Companies dataset (fallback to top-worlds-companies)."""
    logger.info("\n" + "="*60)
    logger.info("Downloading Global Companies dataset (Secondary)")
    logger.info("="*60)
    
    # Authenticate Kaggle
    kaggle.api.authenticate()
    
    # Try multiple dataset options
    dataset_options = [
        "justinas/companies-dataset",  # Original 17M+ dataset
        "bhavikjikadara/top-worlds-companies",  # Fallback: Top world's companies
        "joebeachcapital/top-2000-companies-globally",  # Fallback: Top 2000 companies
    ]
    
    local_path = output_dir / "global_companies"
    local_path.mkdir(exist_ok=True, parents=True)
    
    for dataset in dataset_options:
        try:
            logger.info(f"Trying dataset: {dataset}")
            local_path.mkdir(exist_ok=True, parents=True)
            
            kaggle.api.dataset_download_files(
                dataset,
                path=str(local_path),
                unzip=True,
                quiet=False
            )
            
            # Find CSV files
            csv_files = list(local_path.glob("*.csv"))
            parquet_files = list(local_path.glob("*.parquet"))
            
            if csv_files:
                if len(csv_files) == 1:
                    df = pd.read_csv(csv_files[0])
                else:
                    # Combine multiple CSV files
                    dfs = [pd.read_csv(f) for f in csv_files]
                    df = pd.concat(dfs, ignore_index=True)
                logger.info(f"Successfully downloaded {len(df)} records from {dataset}")
                logger.info(f"Columns: {list(df.columns)}")
                return df
            elif parquet_files:
                if len(parquet_files) == 1:
                    df = pd.read_parquet(parquet_files[0])
                else:
                    dfs = [pd.read_parquet(f) for f in parquet_files]
                    df = pd.concat(dfs, ignore_index=True)
                logger.info(f"Successfully downloaded {len(df)} records from {dataset}")
                logger.info(f"Columns: {list(df.columns)}")
                return df
            else:
                logger.warning(f"No CSV/Parquet files found in {dataset}, trying next...")
                import shutil
                if local_path.exists():
                    shutil.rmtree(local_path)
                local_path.mkdir(exist_ok=True)
                continue
                
        except Exception as e:
            logger.warning(f"Failed to download {dataset}: {e}")
            import shutil
            if local_path.exists():
                shutil.rmtree(local_path)
            local_path.mkdir(exist_ok=True)
            continue
    
    raise Exception("Failed to download any global companies dataset")


def normalize_schema(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Normalize schema to unified format."""
    logger.info(f"\nNormalizing schema for {source_name}...")
    
    df_normalized = df.copy()
    
    # Column mappings
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
    
    # Ensure required columns exist
    required_columns = [
        "company_name", "domain", "industry", "country",
        "employee_count", "revenue", "founded_year"
    ]
    
    for col in required_columns:
        if col not in df_normalized.columns:
            df_normalized[col] = None
    
    # Add metadata
    from datetime import datetime
    df_normalized["source_system"] = source_name
    df_normalized["last_updated_at"] = datetime.utcnow().isoformat()
    
    # Select final columns
    final_columns = required_columns + ["source_system", "last_updated_at"]
    df_normalized = df_normalized[[col for col in final_columns if col in df_normalized.columns]]
    
    return df_normalized


async def enrich_with_web_scraper(df: pd.DataFrame, scraper: WebScraper) -> pd.DataFrame:
    """
    Enrich DataFrame with web-scraped data, focusing on founded_year.
    
    Args:
        df: DataFrame with company data
        scraper: WebScraper instance
        
    Returns:
        Enriched DataFrame
    """
    logger.info("Enriching data with web scraping (focusing on founded_year)...")
    
    # Identify companies missing founded_year
    missing_founded = df['founded_year'].isna() | (df['founded_year'] == '') | (df['founded_year'] == 'None')
    companies_to_enrich = df[missing_founded].copy()
    companies_complete = df[~missing_founded].copy()
    
    if len(companies_to_enrich) == 0:
        logger.info("All companies already have founded_year")
        return df
    
    logger.info(f"Enriching {len(companies_to_enrich)} companies with missing founded_year...")
    
    # Enrich companies
    enriched_list = await scraper.enrich_companies_async(
        companies_to_enrich.to_dict('records')
    )
    enriched_df = pd.DataFrame(enriched_list)
    
    # Merge enriched data back (only update founded_year if it was missing)
    # Reset index to match enriched_df order
    companies_to_enrich_reset = companies_to_enrich.reset_index(drop=True)
    for idx, row in enriched_df.iterrows():
        if pd.notna(row.get('founded_year')) and row.get('founded_year'):
            companies_to_enrich_reset.loc[idx, 'founded_year'] = row.get('founded_year')
    
    # Restore original index
    companies_to_enrich_reset.index = companies_to_enrich.index
    
    # Combine enriched and already complete companies
    final_df = pd.concat([companies_complete, companies_to_enrich_reset], ignore_index=True)
    
    logger.info(f"Successfully enriched {len(companies_to_enrich)} companies with founded_year")
    return final_df


async def main_async():
    """Async main function to download and enrich datasets."""
    logger.info("\n" + "="*60)
    logger.info("Company Atlas - Dataset Download Script with Web Scraping")
    logger.info("="*60)
    
    # Create data directory - use relative path from project root
    data_dir = Path("data/raw")
    data_dir.mkdir(exist_ok=True, parents=True)
    logger.info(f"\nData directory: {data_dir.absolute()}\n")
    
    scraper = WebScraper()
    
    try:
        # Create global_companies subdirectory
        global_companies_dir = data_dir / "global_companies"
        global_companies_dir.mkdir(parents=True, exist_ok=True)
        
        # Download Fortune 1000 dataset
        df_fortune = download_fortune1000(data_dir)
        df_fortune_normalized = normalize_schema(df_fortune, "fortune1000")
        
        # Enrich with web scraping to get founded_year
        logger.info("\n" + "="*60)
        logger.info("Enriching Fortune 1000 data with web scraping")
        logger.info("="*60)
        df_fortune_enriched = await enrich_with_web_scraper(df_fortune_normalized, scraper)
        
        # Save Fortune 1000 as CSV in global_companies subdirectory
        fortune_csv = global_companies_dir / "fortune1000_companies.csv"
        df_fortune_enriched.to_csv(fortune_csv, index=False)
        logger.info(f"\nSaved Fortune 1000 to: {fortune_csv}")
        logger.info(f"   Records: {len(df_fortune_enriched)}")
        logger.info(f"   Records with founded_year: {df_fortune_enriched['founded_year'].notna().sum()}")
        
        # Download Global Companies dataset
        df_global = download_global_companies(data_dir)
        df_global_normalized = normalize_schema(df_global, "global_companies")
        
        # Enrich with web scraping to get founded_year
        logger.info("\n" + "="*60)
        logger.info("Enriching Global Companies data with web scraping")
        logger.info("="*60)
        df_global_enriched = await enrich_with_web_scraper(df_global_normalized, scraper)
        
        # Save Global Companies as CSV in global_companies subdirectory
        global_csv = global_companies_dir / "global_companies.csv"
        df_global_enriched.to_csv(global_csv, index=False)
        logger.info(f"\nSaved Global Companies to: {global_csv}")
        logger.info(f"   Records: {len(df_global_enriched)}")
        logger.info(f"   Records with founded_year: {df_global_enriched['founded_year'].notna().sum()}")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Download Summary")
        logger.info("="*60)
        logger.info(f"Fortune 1000 Companies: {len(df_fortune_enriched)} records")
        logger.info(f"  - With founded_year: {df_fortune_enriched['founded_year'].notna().sum()}")
        logger.info(f"Global Companies: {len(df_global_enriched)} records")
        logger.info(f"  - With founded_year: {df_global_enriched['founded_year'].notna().sum()}")
        logger.info(f"\nFiles saved:")
        logger.info(f"  1. {fortune_csv}")
        logger.info(f"  2. {global_csv}")
        logger.info("="*60)
        
        # Show sample data
        logger.info("\nFortune 1000 Sample:")
        logger.info(df_fortune_enriched.head(3).to_string())
        
        logger.info("\nGlobal Companies Sample:")
        logger.info(df_global_enriched.head(3).to_string())
        
        logger.info("\n✅ Successfully downloaded and enriched both datasets!")
        
        return df_fortune_enriched, df_global_enriched
        
    except Exception as e:
        logger.error(f"\nFailed to download datasets: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await scraper.close()


def main():
    """Main function wrapper to run async code."""
    trio.run(main_async)


if __name__ == "__main__":
    main()

