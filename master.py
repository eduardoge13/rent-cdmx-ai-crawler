import json
from bs4 import BeautifulSoup
import random
from typing import List, Set, Tuple
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

from models.house import House
from utils.data_utils import is_complete_venue, is_duplicate_venue, save_venues_to_csv
from utils.scraper_utils import get_browser_config, get_llm_strategy, is_same_page_as_previous, fetch_and_process_page
# pruebas al crawler
# 1. testear el crawler con una sola url
results = []
browser_config = get_browser_config()
llm_strategy = get_llm_strategy()


url = "https://www.inmuebles24.com/inmuebles-en-renta-en-ciudad-de-mexico"
css_selector = "[class^='postingCard-module__posting-top']"
REQUIRED_KEYS = [
    "Address",
    "Price",
    "Rooms",
    "Neighborhood",
    "City_Province",
    "Square_foot_units_square_meters",
    "Commodities",
]

async def crawl_venues():
    """
    Main function to crawl venue data from the website.
    """
    # Initialize configurations
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy()
    session_id = "house_crawl_session"

    # Initialize state variables
    page_number = 1
    all_venues = []
    seen_names = set()

    # Start the web crawler context
    # https://docs.crawl4ai.com/api/async-webcrawler/#asyncwebcrawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            # Fetch and process data from the current page
            venues, no_results_found = await fetch_and_process_page(
                crawler,
                page_number,
                url,
                css_selector,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_names,
            )

            if no_results_found:
                print("No more pages available. Ending crawl.")
                break  # Stop crawling when the page is the same as before

            if not venues:
                print(f"No houses or departments extracted from page {page_number}.")
                break  # Stop if no houses are extracted

            # Add the venues from this page to the total list
            all_venues.extend(venues)
            page_number += 1  # Move to the next page

            # Pause
            await asyncio.sleep(random.uniform(2,5))  # Adjust sleep time as needed

    # Save the collected venues to a CSV file
    if all_venues:
        save_venues_to_csv(all_venues, "complete_venues.csv")
        print(f"Saved {len(all_venues)} venues to 'complete_venues.csv'.")
    else:
        print("No venues were found during the crawl.")

    # Display usage statistics for the LLM strategy
    llm_strategy.show_usage()

# copy de la función fetch and process page
async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    url = f"{base_url}-pagina-{page_number}.html"
    print(f"Loading page {page_number}...")

    # Check if "No Results Found" message is present
    if await is_same_page_as_previous(url):
        print(f"Skipping page {page_number} as it is the same as the previous crawl.")  
        return [], True  # No more results, signal to stop crawling

    # Fetch page content
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            css_selector=None,  # Fetch the raw HTML without targeting specific content
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not result.success:
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    # Parse the raw HTML using BeautifulSoup
    soup = BeautifulSoup(result.cleaned_html, "html.parser")

    # Extract elements matching the CSS selector
    filtered_elements = soup.select(css_selector)
    filtered_html = "\n".join(str(element) for element in filtered_elements)

    # Save the filtered HTML for debugging (optional)
    html_file_path = f"filtered_page_{page_number}_content.html"
    with open(html_file_path, "w", encoding="utf-8") as html_file:
        html_file.write(filtered_html)
    print(f"Filtered HTML content for page {page_number} saved to {html_file_path}")

    # Pass the filtered HTML to the LLM for extraction
    llm_result = await crawler.arun(
        url=url,  # Use the original URL
        config=CrawlerRunConfig(
            extraction_strategy=llm_strategy,  # Use the LLM strategy
            css_selector=None,  # Pass the filtered HTML directly
            session_id=session_id,  # Unique session ID for the crawl
        ),
        input_data=filtered_html,  # Pass the filtered HTML as input
    )

    if not (llm_result.success and llm_result.extracted_content):
        print(f"Error extracting data from page {page_number}: {llm_result.error_message}")
        return [], False

    # Parse the extracted JSON content
    extracted_data = json.loads(llm_result.extracted_content)

    # Process venues
    complete_venues = []
    for venue in extracted_data:
        if not is_complete_venue(venue, required_keys):
            continue  # Skip incomplete venues

        if is_duplicate_venue(venue["Address"], seen_names):
            print(f"Duplicate venue '{venue['Address']}' found. Skipping.")
            continue  # Skip duplicate venues

        seen_names.add(venue["Address"])
        complete_venues.append(venue)

    if not complete_venues:
        print(f"No complete venues found on page {page_number}.")
        return [], False

    print(f"Extracted {len(complete_venues)} venues from page {page_number}.")
    return complete_venues, False  # Continue crawling
# test
if __name__ == "__main__":
    asyncio.run(crawl_venues())