import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import pickle
import os
import time

# Base URL for IPL matches
url = "https://www.iplt20.com/matches/results/2025#:~:text=View%20all%20IPL%202025%20match%20results%20with%20detailed,Stay%20updated%20with%20every%20match%20outcome%20on%20IPLT20."

def get_match_link():
    match_link = []
    driver = webdriver.Chrome()  # Or any driver you're using
    try:
        driver.get(url)  # Replace with your target URL
        # Wait for the dynamic content to load
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        ul = soup.find('ul', id='team_archive')

        if not ul:
            print("Could not find team_archive element, trying alternative selectors")
            # Try alternative ways to find the match links
            # This is a fallback in case the website structure changes
            match_containers = soup.find_all("div", {"class": "vn-ticketWrapper"})
            if match_containers:
                for container in match_containers:
                    links = container.find_all("a")
                    for link in links:
                        if "/match/2025/" in link.get("href", ""):
                            match_link.append(link.get("href"))
        else:
            bigboxes = ul.find_all('li')
            for i in range(1, len(bigboxes)):
                try:
                    b = bigboxes[i].findAll("div", {"class": "vn-ticnbtn"})
                    if b and len(b[0].findAll("a")) >= 3:
                        link = b[0].findAll("a")[2].get("href")
                        print(f"Found match link: {link}")
                        match_link.append(link)
                except Exception as e:
                    print(f"Error processing box {i}: {e}")

        # Save match links to file for other components to access
        save_match_links(match_link)
        
        return match_link
    except Exception as e:
        print(f"Error in get_match_link: {e}")
        # If scraping fails, try to load from saved file
        if os.path.exists("match_links.pkl"):
            return load_match_links()
        return []
    finally:
        driver.quit()

def save_match_links(links):
    """Save match links to pickle file for persistence"""
    try:
        with open("match_links.pkl", "wb") as f:
            pickle.dump(links, f)
        print(f"Saved {len(links)} match links to file")
    except Exception as e:
        print(f"Error saving match links: {e}")

def load_match_links():
    """Load match links from pickle file"""
    try:
        with open("match_links.pkl", "rb") as f:
            links = pickle.load(f)
        print(f"Loaded {len(links)} match links from file")
        return links
    except Exception as e:
        print(f"Error loading match links: {e}")
        return []

# Get match status - whether it's live or completed
def get_match_status(match_url):
    """Check if a match is live or completed"""
    try:
        driver = webdriver.Chrome()
        driver.get(match_url)
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for live indicators
        live_indicators = [
            soup.find("div", {"class": "liveIndicator"}),
            soup.find("span", text="LIVE"),
            soup.find("div", text="Match in progress")
        ]
        
        # Check if any live indicators were found
        is_live = any(indicator is not None for indicator in live_indicators)
        
        return "live" if is_live else "completed"
    except Exception as e:
        print(f"Error checking match status: {e}")
        return "unknown"
    finally:
        driver.quit()

# If run directly, test the functions
if __name__ == "__main__":
    links = get_match_link()
    print(f"Found {len(links)} match links")
    
    if links:
        # Test status of first match
        status = get_match_status(links[0])
        print(f"First match status: {status}")