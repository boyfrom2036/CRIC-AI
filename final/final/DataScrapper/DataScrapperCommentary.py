from selenium import webdriver
from bs4 import BeautifulSoup
import time
import pickle
import os
from typing import List, Union

# Create a single WebDriver instance
driver = None

def initialize_driver():
    """Initialize the WebDriver if not already initialized"""
    global driver
    if driver is None:
        driver = webdriver.Chrome()
    return driver

def close_driver():
    """Close the WebDriver if it exists"""
    global driver
    if driver is not None:
        driver.quit()
        driver = None

def get_commentary_js(innings_val: str, url: str) -> List[str]:
    """
    Get commentary for a specific innings from a match URL
    
    Args:
        innings_val: The innings number (usually "1" or "2")
        url: The match URL
        
    Returns:
        List of commentary strings or a message if not available
    """
    global driver
    
    try:
        # Initialize driver if needed
        if driver is None:
            driver = webdriver.Chrome()
        
        # Load the page
        driver.get(url)
        time.sleep(5)  # Wait for page to fully load
        
        # Check if the match is live or completed
        is_live = check_if_live(driver)
        
        # Try to set the innings using JavaScript
        try:
            # Set the dropdown value using JS
            driver.execute_script(f"""
                const dropdown = document.querySelector('select.mcSelectDefault.inningsList');
                if (dropdown) {{
                    dropdown.value = '{innings_val}';
                    const event = new Event('change', {{ bubbles: true }});
                    dropdown.dispatchEvent(event);
                }}
            """)
            time.sleep(3)  # Wait for commentary to load
        except Exception as e:
            print(f"Error setting innings: {e}")
            # If we can't set innings, continue with whatever is displayed
        
        # Now extract the commentary
        return extract_commentary(driver)
        
    except Exception as e:
        print(f"Error in get_commentary_js: {e}")
        return ["Error fetching commentary. Please try again."]

def extract_commentary(driver) -> List[str]:
    """Extract commentary from the current page"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Try different selectors for commentary text
    selectors = [
        {"class": "cmdText ng-scope"},
        {"class": "cmdOver"}
    ]
        # bigboxes = soup.find_all("div", {"class": "commentaryText"})
    bigboxes1 = soup.find_all("div", {"class": "cmdText"})
    runOver = soup.find_all("p", {"class": "cmdOver"})
    commentary = [box.text.strip() for box in bigboxes1]
    # print(commentary[1])
    run_and_Over = [box.text.strip() for box in runOver]
    cleaned = [item for item in run_and_Over if item.strip() != '']
    # print(run_and_Over[1])
    result = ["Over- " + str(x) + " " + "Runs- " + str(y) for x, y in zip(cleaned, commentary)]
    if len(result) > 0:
        # Save commentary for caching
        save_commentary(result)
        return result
    # bigboxes = soup.find_all("div", {"class": "cmdText ng-scope"})
    # runOver = soup.find_all("p", {"class": "cmdOver"})
    # commentary = [box.text.strip() for box in bigboxes]
    # print(commentary[0])
    # run_and_Over = [box.text.strip() for box in runOver]
    # print(run_and_Over[0])
    # result = [str(x) + " " + str(y) for x, y in zip(run_and_Over, commentary)]
    # if len(result) > 0:
    #             # Save commentary for caching
    #             save_commentary(result)
    #             return result
    
    # for selector in selectors:
    #     bigboxes = soup.find_all("div", selector)
    #     if bigboxes:
    #         commentary = [box.text.strip() for box in bigboxes]
    #         if len(commentary) > 0:
    #             # Save commentary for caching
    #             save_commentary(commentary)
    #             return commentary
    
    # If no commentary found, try to load from cache
    cached_commentary = load_commentary()
    if cached_commentary:
        return cached_commentary
    
    return ["No commentary available for this match or innings yet."]

def check_if_live(driver) -> bool:
    """Check if the current match is live"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Look for live indicators
    live_indicators = [
        soup.find("div", {"class": "liveIndicator"}),
        soup.find("span", text="LIVE"),
        soup.find("div", text="Match in progress")
    ]
    
    # Check if any live indicators were found
    return any(indicator is not None for indicator in live_indicators)

def save_commentary(commentary: List[str]):
    """Save commentary to pickle file for caching"""
    try:
        with open("commentary_cache.pkl", "wb") as f:
            pickle.dump(commentary, f)
    except Exception as e:
        print(f"Error saving commentary: {e}")

def load_commentary() -> List[str]:
    """Load commentary from pickle file"""
    try:
        if os.path.exists("commentary_cache.pkl"):
            with open("commentary_cache.pkl", "rb") as f:
                return pickle.load(f)
    except Exception as e:
        print(f"Error loading commentary: {e}")
    return []

