"""
Script to enrich Fortune 1000 companies with founded_year using Anthropic API.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enrich_with_anthropic():
    """Enrich Fortune 1000 companies with founded_year using Anthropic API."""
    
    # Read the Fortune 1000 CSV
    csv_file = Path('data/raw/global_companies/fortune1000_companies.csv')
    if not csv_file.exists():
        logger.error(f"File not found: {csv_file}")
        return
    
    logger.info(f"Reading {csv_file}...")
    df = pd.read_csv(csv_file)
    logger.info(f"Loaded {len(df)} companies")
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        return
    
    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)
    
    # Get list of company names
    company_names = df['company_name'].tolist()
    logger.info(f"Preparing to get founded_year for {len(company_names)} companies...")
    
    # Process in batches to avoid token limits
    batch_size = 100
    all_founded_years = {}
    
    # Try different model names (in order of preference)
    model_names = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    
    working_model = None
    for model_name in model_names:
        try:
            # Test with a small request
            test_message = client.messages.create(
                model=model_name,
                max_tokens=4096 if "haiku" in model_name else 16000,
                messages=[{"role": "user", "content": "test"}]
            )
            working_model = model_name
            logger.info(f"Using model: {working_model}")
            break
        except Exception as e:
            logger.debug(f"Model {model_name} not available: {e}")
            continue
    
    if working_model is None:
        raise Exception("No working Anthropic model found. Please check your API key and available models.")
    
    max_tokens = 4096 if "haiku" in working_model else 16000
    
    try:
        total_batches = (len(company_names) + batch_size - 1) // batch_size
        logger.info(f"Processing {total_batches} batches of {batch_size} companies each...")
        
        for batch_idx in range(0, len(company_names), batch_size):
            batch = company_names[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} companies)...")
            
            # Create prompt for this batch
            companies_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(batch, start=1)])
            
            prompt = f"""Please provide the founding year for each of the following Fortune 1000 companies. 
Return the data as a JSON object where each key is the company name (exactly as provided) and the value is the founding year as an integer.
If you don't know the founding year for a company, use null for that value.

Companies:
{companies_text}

Return ONLY a valid JSON object in this format:
{{
  "Walmart": 1962,
  "Amazon": 1994,
  "Apple": 1976,
  ...
}}

Do not include any explanation or additional text, only the JSON object."""

            try:
                message = client.messages.create(
                    model=working_model,
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                # Extract JSON from response
                response_text = message.content[0].text.strip()
                
                # Try to extract JSON if it's wrapped in markdown code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                batch_founded_years = json.loads(response_text)
                all_founded_years.update(batch_founded_years)
                
                logger.info(f"Batch {batch_num}: Retrieved {len(batch_founded_years)} founded years")
                
            except json.JSONDecodeError as e:
                logger.warning(f"Batch {batch_num}: Failed to parse JSON: {e}")
                logger.debug(f"Response (first 500 chars): {response_text[:500]}")
            except Exception as e:
                logger.warning(f"Batch {batch_num}: Error: {e}")
        
        logger.info(f"Successfully retrieved founded_year for {len(all_founded_years)} companies total")
        
        # Update the dataframe
        updated_count = 0
        for company_name, founded_year in all_founded_years.items():
            # Find matching row (case-insensitive)
            mask = df['company_name'].str.strip().str.lower() == company_name.strip().lower()
            if mask.any() and founded_year is not None:
                df.loc[mask, 'founded_year'] = int(founded_year)
                updated_count += 1
        
        logger.info(f"Updated {updated_count} companies with founded_year")
        
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
        enriched_sample = df[df['founded_year'].notna()].head(10)
        if len(enriched_sample) > 0:
            logger.info(f"\nSample of enriched companies:")
            for _, row in enriched_sample.iterrows():
                logger.info(f"  {row['company_name']}: founded_year = {int(row['founded_year'])}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response text (first 500 chars): {response_text[:500]}")
    except Exception as e:
        logger.error(f"Error during enrichment: {e}", exc_info=True)


if __name__ == "__main__":
    enrich_with_anthropic()

