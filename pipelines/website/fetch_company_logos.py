"""
Script to fetch company logos for the top 6 companies by market cap.
Downloads SVG logos and stores them in website/assets/logos/
Uses async/await with trio for concurrent fetching.
"""

import trio
import httpx
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SVG logo URLs - prioritizing transparent SVG sources
# Using Simple Icons (simpleicons.org) for better SVG logos with transparent backgrounds
SVG_LOGO_URLS = {
    "APPLE": "https://cdn.simpleicons.org/apple/000000",
    "MICROSOFT": "https://cdn.simpleicons.org/microsoft/00A4EF",
    "NVIDIA": "https://cdn.simpleicons.org/nvidia/76B900",
    "ALPHABET": "",  # Handled separately with custom SVG
    "AMAZON": "https://cdn.simpleicons.org/amazon/FF9900",
    "META PLATFORMS": "https://cdn.simpleicons.org/meta/0081FB"
}

# Fallback: Clearbit logo API
CLEARBIT_LOGO_URLS = {
    "APPLE": "https://logo.clearbit.com/apple.com",
    "MICROSOFT": "https://logo.clearbit.com/microsoft.com",
    "NVIDIA": "https://logo.clearbit.com/nvidia.com",
    "ALPHABET": "https://logo.clearbit.com/google.com",
    "AMAZON": "https://logo.clearbit.com/amazon.com",
    "META PLATFORMS": "https://logo.clearbit.com/meta.com"
}

# Company websites for domain-based fetching
COMPANY_WEBSITES = {
    "APPLE": "apple.com",
    "MICROSOFT": "microsoft.com",
    "NVIDIA": "nvidia.com",
    "ALPHABET": "google.com",
    "AMAZON": "amazon.com",
    "META PLATFORMS": "meta.com"
}

# HTTP headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/svg+xml,image/*,*/*'
}

def get_google_g_logo() -> bytes:
    """Get the colored Google G icon SVG."""
    # Google's G logo colors: Blue (#4285F4), Red (#EA4335), Yellow (#FBBC05), Green (#34A853)
    google_g_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
</svg>'''
    
    return google_g_svg.encode('utf-8')

async def fetch_svg_logo(client: httpx.AsyncClient, company_name: str) -> bytes:
    """Fetch SVG logo from Simple Icons or Wikimedia (better quality, transparent backgrounds)."""
    try:
        # Special handling for Alphabet/Google G icon
        if company_name.upper() == "ALPHABET":
            logger.info("Fetching Google G icon for ALPHABET")
            return get_google_g_logo()
        
        url = SVG_LOGO_URLS.get(company_name.upper())
        if not url:
            return None
        
        response = await client.get(url, timeout=10.0, headers=HEADERS)
        
        if response.status_code == 200:
            content = response.content
            # Verify it's actually SVG
            content_str = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else str(content)
            if b'<svg' in content or content_str.strip().startswith('<svg'):
                source = "Wikimedia" if "wikimedia" in url else "Simple Icons"
                logger.info(f"✅ Fetched SVG from {source} for {company_name}")
                return content
            else:
                logger.warning(f"Source returned non-SVG for {company_name}")
                return None
        else:
            logger.warning(f"Failed to fetch SVG for {company_name}: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching SVG logo for {company_name}: {e}")
        return None

async def fetch_logo_clearbit(client: httpx.AsyncClient, company_name: str, website: str = None) -> bytes:
    """Fetch logo from Clearbit (fallback)."""
    try:
        if website:
            url = f"https://logo.clearbit.com/{website}"
        else:
            url = CLEARBIT_LOGO_URLS.get(company_name.upper())
        
        if not url:
            return None
        
        response = await client.get(url, timeout=10.0, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching Clearbit logo for {company_name}: {e}")
        return None

async def fetch_logo(client: httpx.AsyncClient, company_name: str, website: str = None) -> bytes:
    """Fetch logo for a company, prioritizing SVG with transparent backgrounds."""
    # First try Simple Icons (SVG with transparent backgrounds)
    logo_data = await fetch_svg_logo(client, company_name)
    
    if logo_data:
        return logo_data
    
    # Fallback to Clearbit
    logger.info(f"Falling back to Clearbit for {company_name}")
    return await fetch_logo_clearbit(client, company_name, website)

def determine_file_extension(logo_data: bytes) -> str:
    """Determine file extension based on logo data."""
    if logo_data.startswith(b'<svg') or b'<svg' in logo_data[:100]:
        return 'svg'
    elif logo_data.startswith(b'\x89PNG'):
        return 'png'
    elif logo_data.startswith(b'\xff\xd8'):
        return 'jpg'
    else:
        return 'svg'  # Default to SVG

def save_logo(logo_data: bytes, company_name: str, logos_dir: Path) -> bool:
    """Save logo to file."""
    try:
        ext = determine_file_extension(logo_data)
        logo_filename = f"{company_name.replace(' ', '_').lower()}.{ext}"
        logo_path = logos_dir / logo_filename
        
        # For SVG, ensure it's saved as UTF-8 text
        if ext == 'svg':
            content_str = logo_data.decode('utf-8', errors='ignore') if isinstance(logo_data, bytes) else str(logo_data)
            with open(logo_path, 'w', encoding='utf-8') as f:
                f.write(content_str)
        else:
            with open(logo_path, 'wb') as f:
                f.write(logo_data)
        
        logger.info(f"✅ Saved logo: {logo_path} ({ext.upper()})")
        return True
    except Exception as e:
        logger.error(f"Error saving logo for {company_name}: {e}")
        return False

async def fetch_company_logo(
    client: httpx.AsyncClient,
    company: dict,
    logos_dir: Path,
    nursery: trio.Nursery
) -> None:
    """Fetch logo for a single company (async task)."""
    company_name = company.get('company_name', '').upper()
    website = company.get('website', '')
    
    # Extract domain from website URL
    domain = None
    if website:
        domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
    
    # Special handling for Alphabet (use Google) and Meta (use meta.com)
    if company_name == "ALPHABET":
        logger.info(f"Fetching logo for {company_name} (using google.com)")
        logo_data = await fetch_logo(client, company_name, "google.com")
    elif company_name == "META PLATFORMS":
        logger.info(f"Fetching logo for {company_name} (using meta.com)")
        logo_data = await fetch_logo(client, company_name, "meta.com")
    else:
        logger.info(f"Fetching logo for {company_name} (domain: {domain})")
        logo_data = await fetch_logo(client, company_name, domain)
    
    if logo_data:
        save_logo(logo_data, company_name, logos_dir)
    else:
        logger.warning(f"⚠️  Could not fetch logo for {company_name}")

async def main_async():
    """Main async function to fetch logos for top companies."""
    # Load company data to get top 6
    data_file = Path('data/marts/unified_companies.json')
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return
    
    with open(data_file, 'r') as f:
        companies = json.load(f)
    
    # Get top 6 by market cap
    top_companies = sorted(
        [c for c in companies if c.get('market_cap_updated_m')],
        key=lambda x: x.get('market_cap_updated_m', 0),
        reverse=True
    )[:6]
    
    # Create logos directory
    logos_dir = Path('website/assets/logos')
    logos_dir.mkdir(parents=True, exist_ok=True)
    
    # Create HTTP client
    async with httpx.AsyncClient() as client:
        # Fetch all logos concurrently using trio nursery
        async with trio.open_nursery() as nursery:
            for company in top_companies:
                nursery.start_soon(fetch_company_logo, client, company, logos_dir)
    
    logger.info("✅ Logo fetching complete!")

def main():
    """Entry point - runs async main with trio."""
    trio.run(main_async)

if __name__ == "__main__":
    main()
