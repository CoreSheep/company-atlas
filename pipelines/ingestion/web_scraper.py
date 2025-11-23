"""
Async web scraper using trio for fast company data enrichment.
Scrapes Wikipedia and other sources to get missing company information.
"""

import re
import logging
from typing import Dict, Optional, List
from urllib.parse import quote, urljoin
import trio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User agent to avoid blocking
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Rate limiting: max concurrent requests
MAX_CONCURRENT = 50
# Delay between requests (in seconds)
REQUEST_DELAY = 0.1


class WebScraper:
    """Async web scraper for company data enrichment using trio."""
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT, delay: float = REQUEST_DELAY):
        """
        Initialize web scraper.
        
        Args:
            max_concurrent: Maximum concurrent requests
            delay: Delay between requests in seconds
        """
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.semaphore = trio.Semaphore(max_concurrent)
        self.client: Optional[httpx.AsyncClient] = None
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": USER_AGENT},
                limits=httpx.Limits(max_connections=self.max_concurrent),
                follow_redirects=True
            )
        return self.client
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
        self.client = None
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL content asynchronously with rate limiting using trio and httpx.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if failed
        """
        async with self.semaphore:
            try:
                await trio.sleep(self.delay)  # Rate limiting
                client = self._get_http_client()
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.debug(f"HTTP {response.status_code} for {url}")
                    return None
            except httpx.HTTPStatusError as e:
                logger.debug(f"HTTP error {e.response.status_code} for {url}")
                return None
            except Exception as e:
                # Catch all other exceptions silently
                logger.debug(f"Failed to fetch {url}: {str(e)[:50]}")
                return None
    
    def parse_wikipedia_infobox(self, html: str) -> Dict[str, Optional[str]]:
        """
        Parse Wikipedia infobox for company information.
        
        Args:
            html: HTML content from Wikipedia page
            
        Returns:
            Dictionary with company information
        """
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Find infobox
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            return data
        
        # Extract data from infobox rows
        rows = infobox.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text(strip=True).lower()
                value = td.get_text(strip=True)
                
                # Map Wikipedia keys to our fields
                if 'website' in key or 'web' in key:
                    # Extract domain from URL
                    links = td.find_all('a', href=True)
                    if links:
                        url = links[0].get('href', '')
                        domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                        if domain:
                            data['domain'] = domain.group(1).lower()
                    if not data.get('domain'):
                        data['domain'] = value.lower()
                
                elif 'industry' in key or 'sector' in key:
                    data['industry'] = value
                
                elif 'founded' in key or 'foundation' in key:
                    # Extract year from founded date
                    year_match = re.search(r'(\d{4})', value)
                    if year_match:
                        data['founded_year'] = int(year_match.group(1))
                    else:
                        data['founded_year'] = None
                
                elif 'employees' in key or 'workforce' in key:
                    # Extract number from employee count
                    num_match = re.search(r'([\d,]+)', value.replace(',', ''))
                    if num_match:
                        data['employee_count'] = int(num_match.group(1).replace(',', ''))
                
                elif 'revenue' in key:
                    # Extract revenue number (handle various formats)
                    # Remove currency symbols and extract numbers
                    revenue_text = re.sub(r'[^\d.,]', '', value)
                    revenue_match = re.search(r'([\d.,]+)', revenue_text)
                    if revenue_match:
                        revenue_str = revenue_match.group(1).replace(',', '')
                        # Check if it's in millions or billions
                        if 'billion' in value.lower() or 'bn' in value.lower():
                            data['revenue'] = float(revenue_str) * 1_000_000_000
                        elif 'million' in value.lower() or 'mn' in value.lower() or 'm' in value.lower():
                            data['revenue'] = float(revenue_str) * 1_000_000
                        else:
                            try:
                                data['revenue'] = float(revenue_str)
                            except:
                                pass
        
        # Extract country from location/hq
        location_rows = infobox.find_all('tr')
        for row in location_rows:
            th = row.find('th')
            if th and ('headquarters' in th.get_text(strip=True).lower() or 
                      'location' in th.get_text(strip=True).lower()):
                td = row.find('td')
                if td:
                    # Get country from location
                    location_text = td.get_text(strip=True)
                    # Common country patterns
                    countries = ['USA', 'United States', 'US', 'UK', 'United Kingdom', 'Canada', 
                               'Germany', 'France', 'Japan', 'China', 'India', 'Australia']
                    for country in countries:
                        if country in location_text:
                            data['country'] = country
                            if country in ['USA', 'United States', 'US']:
                                data['country'] = 'USA'
                            elif country in ['UK', 'United Kingdom']:
                                data['country'] = 'UK'
                            break
        
        return data
    
    async def scrape_wikipedia(self, company_name: str) -> Dict[str, Optional[str]]:
        """
        Scrape Wikipedia page for company information.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Dictionary with company information
        """
        # Construct Wikipedia URL
        wiki_url = f"https://en.wikipedia.org/wiki/{quote(company_name)}"
        
        logger.debug(f"Scraping Wikipedia: {wiki_url}")
        html = await self.fetch_url(wiki_url)
        
        if not html:
            return {}
        
        return self.parse_wikipedia_infobox(html)
    
    async def scrape_company_info(self, company_name: str, existing_data: Dict = None) -> Dict[str, Optional[str]]:
        """
        Scrape company information from multiple sources.
        
        Args:
            company_name: Name of the company
            existing_data: Existing company data to merge with
            
        Returns:
            Dictionary with enriched company information
        """
        if existing_data is None:
            existing_data = {}
        
        result = existing_data.copy()
        
        # Try Wikipedia first
        try:
            wiki_data = await self.scrape_wikipedia(company_name)
            # Merge wiki data (only fill missing fields)
            for key, value in wiki_data.items():
                if not result.get(key) and value:
                    result[key] = value
        except Exception as e:
            logger.warning(f"Wikipedia scraping failed for {company_name}: {e}")
        
        # Set defaults
        result['company_name'] = result.get('company_name') or company_name
        result['source_system'] = result.get('source_system') or 'web_scraper'
        result['last_updated_at'] = datetime.utcnow().isoformat()
        
        return result
    
    async def enrich_companies_async(self, companies: List[Dict]) -> List[Dict]:
        """
        Enrich multiple companies concurrently.
        
        Args:
            companies: List of company dictionaries
            
        Returns:
            List of enriched company dictionaries
        """
        results = []
        
        async def enrich_one(company: Dict, result_list: list):
            """Enrich a single company and append to result list."""
            company_name = company.get('company_name') or company.get('name') or ''
            if not company_name:
                result_list.append(company)
                return
            
            try:
                enriched = await self.scrape_company_info(company_name, company)
                result_list.append(enriched)
            except Exception as e:
                # Silently fail and return original company data
                logger.debug(f"Failed to enrich {company_name}: {str(e)[:100]}")
                result_list.append(company)
        
        # Process companies in smaller batches to avoid overwhelming the system
        batch_size = 30
        total_batches = (len(companies) + batch_size - 1) // batch_size
        
        for i in range(0, len(companies), batch_size):
            batch = companies[i:i+batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} companies)...")
            
            batch_results = []
            
            # Use nursery with proper exception handling
        async with trio.open_nursery() as nursery:
                for company in batch:
                    nursery.start_soon(enrich_one, company, batch_results)
            
            # All tasks completed (or failed), add results
            results.extend(batch_results)
            
            # Log progress
            if batch_num % 5 == 0 or batch_num == total_batches:
                enriched_count = sum(1 for r in results if r.get('founded_year') and pd.notna(r.get('founded_year')))
                logger.info(f"Progress: {len(results)}/{len(companies)} processed, {enriched_count} with founded_year")
        
        return results


async def enrich_company_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich a pandas DataFrame with web-scraped data.
    
    Args:
        df: DataFrame with company data
        
    Returns:
        Enriched DataFrame
    """
    import pandas as pd
    
    scraper = WebScraper()
    
    try:
        # Convert DataFrame to list of dicts
        companies = df.to_dict('records')
        
        # Enrich companies
        logger.info(f"Enriching {len(companies)} companies with web scraping...")
        enriched_companies = await scraper.enrich_companies_async(companies)
        
        # Convert back to DataFrame
        enriched_df = pd.DataFrame(enriched_companies)
        
        logger.info(f"Successfully enriched {len(enriched_df)} companies")
        return enriched_df
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    # Test the scraper
    async def test():
        scraper = WebScraper()
        try:
            # Test with a well-known company
            result = await scraper.scrape_company_info("Apple Inc.")
            print(f"Scraped data: {result}")
        finally:
            await scraper.close()
    
    trio.run(test)

