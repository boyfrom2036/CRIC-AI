from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
import requests
import pandas as pd
import time
import re
import logging
# Setup Chrome options for faster loading
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--log-level=3")
# ----------------------------
# Setup Logging
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

def load_data(url):
    driver = webdriver.Chrome()  # Or any driver you're using
    driver.get(url)  # Replace with your target URL

    # Wait for the dynamic content to load (e.g., with time.sleep or WebDriverWait)
    time.sleep(3)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    raw_text = soup.get_text()
    clean_text = re.sub(r'[\n\r\t\b]+', ' ', raw_text)  # Remove newlines, tabs, backspaces
    clean_text = re.sub(r'\s+', ' ', clean_text)        # Replace multiple spaces with a single space
    clean_text = clean_text.strip() 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=450,
        chunk_overlap=70,
        
    )
    logging.info(f"Splitting text into chunks")
    docs=text_splitter.create_documents([clean_text])
    return docs

