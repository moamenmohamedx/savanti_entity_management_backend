"""Wyoming Secretary of State portal scraper."""

from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
import structlog

logger = structlog.get_logger()


class WyomingScraper:
    """Scraper for Wyoming Secretary of State business search portal."""

    PORTAL_URL = "https://wyobiz.wyo.gov/Business/FilingSearch.aspx"

    def __init__(self):
        self.browser: Optional[Browser] = None

    async def _get_browser(self) -> Browser:
        """Initialize browser if not already running."""
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
        return self.browser

    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def search_by_filing_id(self, filing_id: str) -> dict:
        """Search for entity by filing ID on Wyoming SoS portal.
        
        Args:
            filing_id: Wyoming filing/registration number
            
        Returns:
            Dictionary with entity data from state portal:
            - entity_name: str
            - status: str
            - formation_date: str
            - registered_agent: str
        """
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            # Navigate to search page
            await page.goto(self.PORTAL_URL, wait_until="networkidle")
            logger.info("wyoming_scraper_loaded", filing_id=filing_id)

            # Fill in filing ID search field
            await page.fill('input[name*="FilingNumber"]', filing_id)

            # Submit search (handle ASP.NET postback)
            async with page.expect_navigation(wait_until="networkidle"):
                await page.click('input[type="submit"][value*="Search"]')

            # Wait for results
            await page.wait_for_selector('table.results', timeout=10000)

            # Extract entity data from results table
            entity_data = await self._extract_entity_data(page)

            logger.info("wyoming_scraper_success", filing_id=filing_id)
            return entity_data

        except Exception as e:
            logger.error("wyoming_scraper_failed", filing_id=filing_id, error=str(e))
            raise Exception(f"Failed to scrape Wyoming portal: {str(e)}")

        finally:
            await page.close()

    async def _extract_entity_data(self, page: Page) -> dict:
        """Extract entity data from search results page.
        
        Args:
            page: Playwright page with search results loaded
            
        Returns:
            Dictionary with extracted entity information
        """
        # Extract data from results table
        # Note: Actual selectors depend on Wyoming portal's HTML structure
        # This is a simplified implementation

        entity_name = await page.locator('td:has-text("Entity Name") + td').text_content() or ""
        status = await page.locator('td:has-text("Status") + td').text_content() or ""
        formation_date = await page.locator('td:has-text("Formation Date") + td').text_content() or ""
        registered_agent = await page.locator('td:has-text("Registered Agent") + td').text_content() or ""

        return {
            "entity_name": entity_name.strip(),
            "status": status.strip(),
            "formation_date": formation_date.strip(),
            "registered_agent": registered_agent.strip(),
        }

