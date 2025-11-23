"""
Main ingestion script for Company Atlas pipeline.
Uses Fortune 1000 dataset as primary source and enriches with web scraping.
Also downloads the secondary global companies dataset.
"""

import logging
import trio
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from pipelines.ingestion.fortune1000_ingestion import Fortune1000Ingestion
from pipelines.ingestion.kaggle_ingestion import KaggleIngestion

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main ingestion function."""
    logger.info("Starting Company Atlas ingestion pipeline...")
    
    # Create data directory
    data_dir = Path("company-atlas/data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data directory: {data_dir.absolute()}")
    
    try:
        # 1. Download and process Fortune 1000 dataset (primary)
        logger.info("\n" + "="*60)
        logger.info("Step 1: Ingesting Fortune 1000 dataset (Primary)")
        logger.info("="*60)
        
        ingester_fortune = Fortune1000Ingestion(
            output_dir=str(data_dir),
            enrich_with_scraping=False  # Disable scraping for faster initial download
        )
        
        df_fortune = await ingester_fortune.ingest_all()
        
        # Create global_companies subdirectory
        global_companies_dir = data_dir / "global_companies"
        global_companies_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Fortune 1000 as CSV in global_companies subdirectory
        fortune_csv_path = global_companies_dir / "fortune1000_companies.csv"
        df_fortune.to_csv(fortune_csv_path, index=False)
        logger.info(f"Saved Fortune 1000 dataset to: {fortune_csv_path}")
        logger.info(f"   Records: {len(df_fortune)}")
        logger.info(f"   Columns: {list(df_fortune.columns)}")
        
        # 2. Download secondary global companies dataset
        logger.info("\n" + "="*60)
        logger.info("Step 2: Ingesting Global Companies dataset (Secondary)")
        logger.info("="*60)
        
        ingester_global = KaggleIngestion(output_dir=str(data_dir))
        datasets = ingester_global.ingest_all()
        
        if datasets and len(datasets) > 1:
            # Get the second dataset (17M+ companies or fallback)
            df_global = datasets[1]  # Second dataset is the global companies
            
            # Save global companies as CSV in global_companies subdirectory
            global_csv_path = global_companies_dir / "global_companies.csv"
            df_global.to_csv(global_csv_path, index=False)
            logger.info(f"Saved Global Companies dataset to: {global_csv_path}")
            logger.info(f"   Records: {len(df_global)}")
            logger.info(f"   Columns: {list(df_global.columns)}")
        else:
            logger.warning("Global companies dataset not available, skipping...")
            df_global = None
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Ingestion Summary")
        logger.info("="*60)
        logger.info(f"Fortune 1000 Companies: {len(df_fortune)} records")
        if df_global is not None:
            logger.info(f"Global Companies: {len(df_global)} records")
        
        logger.info(f"\nFortune 1000 Missing data summary:")
        missing_summary = df_fortune[['company_name', 'domain', 'industry', 'country', 
                                      'employee_count', 'revenue', 'founded_year']].isnull().sum()
        for col, count in missing_summary.items():
            percentage = (count / len(df_fortune)) * 100 if len(df_fortune) > 0 else 0
            logger.info(f"  {col}: {count} ({percentage:.1f}%)")
        
        logger.info("\n" + "="*60)
        logger.info("Files saved:")
        logger.info(f"  1. {fortune_csv_path}")
        if df_global is not None:
            logger.info(f"  2. {global_csv_path}")
        logger.info("="*60)
        
        return df_fortune, df_global if df_global is not None else None
        
    except Exception as e:
        logger.error(f"Failed to ingest data: {e}", exc_info=True)
        raise
    finally:
        # Close scrapers
        if 'ingester_fortune' in locals() and ingester_fortune.scraper:
            await ingester_fortune.scraper.close()


if __name__ == "__main__":
    try:
        df_fortune, df_global = trio.run(main)
        logger.info(f"\nSuccessfully ingested datasets!")
        logger.info(f"   - Fortune 1000: {len(df_fortune)} companies")
        if df_global is not None:
            logger.info(f"   - Global Companies: {len(df_global)} companies")
    except Exception as e:
        logger.error(f"\nIngestion failed: {e}", exc_info=True)
        sys.exit(1)

