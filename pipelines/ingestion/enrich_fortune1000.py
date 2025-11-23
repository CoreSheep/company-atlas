"""
Script to enrich Fortune 1000 companies with founded_year using web scraping.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import trio
import logging
from datetime import datetime
from pipelines.ingestion.web_scraper import WebScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def enrich_fortune1000_with_founded_year():
    """Enrich Fortune 1000 companies with founded_year from web scraping."""
    
    # Read the Fortune 1000 CSV
    csv_file = Path('data/raw/global_companies/fortune1000_companies.csv')
    if not csv_file.exists():
        logger.error(f"File not found: {csv_file}")
        return
    
    logger.info(f"Reading {csv_file}...")
    df = pd.read_csv(csv_file)
    logger.info(f"Loaded {len(df)} companies")
    
    # Check how many already have founded_year
    has_founded = df['founded_year'].notna().sum()
    logger.info(f"Companies with founded_year: {has_founded} / {len(df)}")
    
    # Filter companies that need enrichment
    needs_enrichment = df[df['founded_year'].isna()].copy()
    logger.info(f"Companies needing enrichment: {len(needs_enrichment)}")
    
    if len(needs_enrichment) == 0:
        logger.info("All companies already have founded_year!")
        return
    
    # Initialize web scraper
    scraper = WebScraper(max_concurrent=20, delay=0.2)  # More conservative rate limiting
    
    try:
        # Convert to list of dicts for enrichment
        companies_to_enrich = needs_enrichment.to_dict('records')
        
        logger.info(f"Starting web scraping enrichment for {len(companies_to_enrich)} companies...")
        logger.info("This may take several minutes...")
        
        # Enrich companies
        enriched_list = await scraper.enrich_companies_async(companies_to_enrich)
        enriched_df = pd.DataFrame(enriched_list)
        
        # Merge enriched data back into original dataframe
        # Create a mapping of company_name to founded_year
        founded_year_map = {}
        for idx, row in enriched_df.iterrows():
            company_name = row.get('company_name')
            founded_year = row.get('founded_year')
            if company_name and pd.notna(founded_year) and founded_year:
                founded_year_map[company_name] = founded_year
        
        # Update the original dataframe
        updated_count = 0
        for company_name, founded_year in founded_year_map.items():
            mask = df['company_name'] == company_name
            if mask.any():
                df.loc[mask, 'founded_year'] = founded_year
                updated_count += 1
        
        logger.info(f"Successfully enriched {updated_count} companies with founded_year")
        
        # Update last_updated_at
        df['last_updated_at'] = datetime.utcnow().isoformat()
        
        # Save back to CSV
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved enriched data to {csv_file}")
        
        # Print summary
        final_count = df['founded_year'].notna().sum()
        logger.info(f"\nFinal summary:")
        logger.info(f"  Total companies: {len(df)}")
        logger.info(f"  Companies with founded_year: {final_count} ({final_count/len(df)*100:.1f}%)")
        logger.info(f"  Companies still missing founded_year: {len(df) - final_count}")
        
        # Show sample of enriched companies
        enriched_sample = df[df['founded_year'].notna()].head(5)
        if len(enriched_sample) > 0:
            logger.info(f"\nSample of enriched companies:")
            for _, row in enriched_sample.iterrows():
                logger.info(f"  {row['company_name']}: founded_year = {row['founded_year']}")
        
    except Exception as e:
        logger.error(f"Error during enrichment: {e}", exc_info=True)
    finally:
        await scraper.close()


async def main():
    """Main async function."""
    await enrich_fortune1000_with_founded_year()


if __name__ == "__main__":
    trio.run(main)

