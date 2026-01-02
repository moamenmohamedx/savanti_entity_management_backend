"""State portal scrapers."""

from .wyoming import WyomingScraper


def get_scraper(state_code: str):
    """Factory to get scraper by state code.
    
    Args:
        state_code: Two-letter state code (e.g., "WY")
        
    Returns:
        Scraper instance for the specified state
        
    Raises:
        ValueError: If no scraper exists for the state
    """
    scrapers = {"WY": WyomingScraper}

    if state_code.upper() not in scrapers:
        raise ValueError(f"No scraper for state: {state_code}")

    return scrapers[state_code.upper()]()


__all__ = ["WyomingScraper", "get_scraper"]

