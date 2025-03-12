#!/usr/bin/env python3
"""
Module for targeted news article search and filtering related to trafficking incidents.

Usage:
    python web_researcher.py --days_back 7

Developer: Christo Strydom
"""

import os
import json
import math
import random
import time
import logging
import pandas as pd
import requests
import tldextract
from typing import List, Optional, Any
from bs4 import BeautifulSoup
from readability import Document
from newspaper import Article
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, WebDriverException

from work_with_db import URLDatabase, DatabaseError
from llama_index.core import Document as liDocument, VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI
from models import (
    ConfirmResponse,
    IncidentResponse,
    SuspectFormResponse,
    SuspectResponse,
    VictimResponse,
    VictimFormResponse
)
from get_urls_from_csvs import get_unique_urls_from_csvs
llm = OpenAI(temperature=0, model="o3-mini", request_timeout=120.0)
memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
# Configure Logging
logging.basicConfig(
    filename="google_search.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Load API credentials from environment variables
API_KEY = os.getenv('GOOGLE_API_KEY')
SEARCH_ENGINE_ID = os.getenv('GOOGLE_CSE_ID')
MIN_TEXT_LENGTH = 100  # adjust as necessary
if not API_KEY or not SEARCH_ENGINE_ID:
    logger.critical("API_KEY and SEARCH_ENGINE_ID must be set as environment variables.")
    exit(1)

# Prompts for chat engine processing
SHORT_PROMPTS = {
    "incident_prompt": (
        "Assistant, please indicate if it can be said with certainty that this article is a factual report of an "
        "actual incident of human trafficking or any closely associated crime."
        "Return your answer in the following RAW JSON format with NO backticks OR code blocks:\n"
        "{\n"
        '  "answer": "yes" or "no",\n'
        '  "evidence": ["incident1", "incident2", "incident3"] or null\n'
        "}"
    ),
    "crime_prompt": (
        "Assistant, please indicate if there is mention of crime in this article. If yes, provide the crime(s) by name. "
        "Return your answer in the following JSON format:\n"
        "{\n"
        '  "answer": "yes" or "no",\n'
        '  "evidence": ["crime1", "crime2", "crime3"] or null\n'
        "}"
    ),
    "suspect_prompt": (
        "Assistant, please indicate if there is mention of suspect(s) of a crime related to human trafficking in this article. "
        "Suspects has to be natural persons that is, the NAME (firstname and/or secondname of suspect) of a person, not organizations or any other entities. Exclude cases involving allegations and cases involving "
        "politicians or celebrities or ANY other sensational reports or reporting."
        "If yes, provide the suspects(s) by name. EXCLUDE ALL other detail and ONLY provide the NAME (firstname and/or secondname of suspect) of the suspect(s)."
        "Return your answer in the following RAW JSON format ONLY and NO backticks and with no code blocks:\n"
        "{\n"
        '  "answer": "yes" or "no",\n'
        '  "evidence": ["firstname and/or secondname of suspect1", '
        '"firstname and/or secondname of suspect2", "firstname and/or secondname of suspect3", ...] or null\n'
        "}"
    ),
    "victim_prompt": (
        "Assistant, the following is a list of named suspects in the accompanying article.  Please indicate if there is mention of victim(s) of a crime related to human trafficking in this article. "
        "Victims have to be natural persons that is, the NAME (firstname and/or secondname of victim) of a person, not organizations or any other entities. Exclude cases involving allegations and cases involving "
        "politicians or celebrities or ANY other sensational reports or reporting."
        "If yes, provide the victim(s) by name. EXCLUDE ALL other detail and ONLY provide the NAME (firstname and/or secondname of victim) of the victim(s)."
        "Return your answer in the following RAW JSON format ONLY with NO backticks and with NO code blocks:\n"
        "{\n"
        '  "answer": "yes" or "no",\n'
        '  "evidence": ["firstname and/or secondname of victim1", '
        '"firstname and/or secondname of victim2", "firstname and/or secondname of victim2", ...] or null\n'
        "}"
    ),
}

# --- Extraction Methods ---

def extract_with_newspaper(url: str) -> str:
    """Try to extract the article text using newspaper3k."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()
        if len(text) >= MIN_TEXT_LENGTH:
            logger.info("Article extracted successfully using newspaper3k.")
            return text
        else:
            logger.warning("Newspaper3k extraction returned insufficient text.")
    except Exception as e:
        logger.error(f"Error using newspaper3k for {url}: {e}")
    return ""

def extract_with_readability(url: str) -> str:
    """Fetch the page with requests and extract text using readability-lxml."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.85 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Requests returned status code {response.status_code} for {url}")
            return ""
        doc = Document(response.text)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator="\n").strip()
        if len(text) >= MIN_TEXT_LENGTH:
            logger.info("Article extracted successfully using readability-lxml.")
            return text
        else:
            logger.warning("Readability extraction returned insufficient text.")
    except Exception as e:
        logger.error(f"Error using readability for {url}: {e}")
    return ""

def extract_with_selenium(url: str) -> str:
    """Render the page with Selenium and extract the main content."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.85 Safari/537.36"
        )
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        time.sleep(3)  # Allow time for dynamic content to load
        html = driver.page_source
        driver.quit()
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator="\n").strip()
        if len(text) >= MIN_TEXT_LENGTH:
            logger.info("Article extracted successfully using Selenium with readability.")
            return text
        else:
            logger.warning("Selenium extraction returned insufficient text.")
    except Exception as e:
        logger.error(f"Error using Selenium for {url}: {e}")
    return ""

def extract_main_text(url: str) -> str:
    """
    Extracts the main text from an article URL using multiple fallback methods.
    1. Try newspaper3k.
    2. Fall back to requests + readability-lxml.
    3. Finally, use Selenium to render JavaScript.
    """
    logger.info(f"Attempting to extract article text from {url}")
    text = extract_with_newspaper(url)
    if text:
        return text
    text = extract_with_readability(url)
    if text:
        return text
    return extract_with_selenium(url)

# --- Google Search Functions (if needed externally) ---

def google_search(query, api_key, cse_id, start, num=10):
    """
    Performs a Google Custom Search and returns the search results.
    """
    service = build("customsearch", "v1", developerKey=api_key)
    try:
        res = service.cse().list(q=query, cx=cse_id, num=num, start=start).execute()
        return res.get('items', [])
    except HttpError as e:
        error_content = e.content.decode('utf-8')
        logger.error(f"HTTP Error {e.resp.status}: {error_content}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error during Google Search API call: {e}")
        return []

def fetch_all_results(query, api_key, cse_id, max_results=30):
    """
    Fetches all search results up to the specified maximum.
    """
    results = []
    num_per_page = 10
    total_pages = math.ceil(max_results / num_per_page)
    for page in range(total_pages):
        start = 1 + page * num_per_page
        logger.info(f"Fetching page {page + 1} with start={start}")
        page_results = google_search(query, api_key, cse_id, start, num=num_per_page)
        if not page_results:
            logger.warning(f"No results returned for start={start}. Ending search.")
            break
        results.extend(page_results)
        time.sleep(1)
    return results[:max_results]

# --- Selenium and URL Utilities ---

def initialize_selenium() -> Optional[webdriver.Chrome]:
    """
    Initializes the Selenium WebDriver with headless Chrome.
    """
    try:
        driver_path = "/opt/homebrew/bin/chromedriver"  # Update as needed
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/85.0.4183.102 Safari/537.36"
        )
        driver = webdriver.Chrome(service=ChromeService(driver_path), options=chrome_options)
        logger.info("Selenium WebDriver initialized successfully.")
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Selenium WebDriver: {e}")
        return None

def is_url_accessible(url: str) -> bool:
    """Simple check to determine if a URL is accessible via Selenium."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.85 Safari/537.36"
    )
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        status = driver.title != ""
        driver.quit()
        return status
    except Exception as e:
        logger.error(f"Exception for URL {url}: {e}")
        return False

def fetch_url_with_retries(driver, url, max_retries=3, retry_delay=5) -> bool:
    """Attempts to load a URL with retries."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt} to load URL: {url}")
            driver.get(url)
            logger.info(f"Successfully loaded URL: {url}")
            return True
        except TimeoutException:
            logger.warning(f"Attempt {attempt} timed out for URL: {url}")
        except WebDriverException as e:
            logger.error(f"WebDriverException on attempt {attempt} for URL {url}: {e}")
            break
        time.sleep(retry_delay)
    logger.error(f"Failed to load URL after {max_retries} attempts: {url}")
    return False

def get_new_urls(new_urls: List[str]) -> List[str]:
    """
    Returns URLs that are not already in the database.
    """
    db = URLDatabase()
    df = pd.DataFrame(db.search_urls(limit=1000000))
    db_urls = df['url'].tolist()
    return list(set(new_urls) - set(db_urls))

# --- Chat Engine Helpers ---

def get_validated_response(prompt_key: str, prompt_text: str, model_class: Any, chat_engine) -> Optional[Any]:
    """
    Sends a prompt to the chat engine and validates the JSON response.
    """
    max_retries = 5
    base_delay = 5
    for attempt in range(max_retries):
        try:
            response = chat_engine.chat(prompt_text)
            logger.info(f"Prompt '{prompt_key}' processed successfully.")
            response_data = model_class.model_validate_json(response.response)
            return response_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed for '{prompt_key}': {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for '{prompt_key}': {e}")
        except Exception as e:
            if "429 Too Many Requests" in str(e):
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limit hit. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to parse response for '{prompt_key}': {e}")
                return None
    logger.error(f"Max retries reached for '{prompt_key}'. Skipping...")
    return None

def verify_incident(url: str, chat_engine):
    """
    Verifies whether an article reports an actual incident.
    """
    db = URLDatabase()
    result = {"actual_incident": -2}
    incidents = []
    try:
        prompt_key = "incident_prompt"
        prompt_text = SHORT_PROMPTS[prompt_key]
        response_data = get_validated_response(prompt_key, prompt_text, IncidentResponse, chat_engine)
        if response_data is None:
            logger.warning(f"No valid response for URL: {url}")
            return result, incidents
        response_answer = response_data.answer.lower()
        if response_answer == "no":
            logger.info(f"No incident detected for URL: {url}")
            db.update_field(url, "actual_incident", 0)
            result["actual_incident"] = 0
            return result, incidents
        if response_answer == "yes":
            logger.info(f"Incident detected for URL: {url}")
            db.update_field(url, "actual_incident", 1)
            result["actual_incident"] = 1
            incidents = response_data.evidence or []
            return result, incidents
        logger.warning(f"Unexpected response for URL: {url} - {response_data.answer}")
        return result, incidents
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return result, incidents

def confirm_natural_name(name: str) -> bool:
    """
    Confirm if the provided string qualifies as a natural person's name.
    """
    try:
        llm = OpenAI(temperature=0, model="o3-mini", request_timeout=120.0)
        prompt_text = (
            f"Assistant, please evaluate the following string: '{name}'. "
            "Determine whether this string is used to identify a natural person. "
            "Return your answer in the following RAW JSON format ONLY and WITHOUT any backticks or additional commentary:\n"
            "{\"answer\": \"yes\" or \"no\"}"
        )
        resp = llm.complete(prompt_text)
        response_data = ConfirmResponse.model_validate_json(resp.text)
        return response_data is not None and response_data.answer.lower() == "yes"
    except Exception as e:
        logger.error(f"Failed to confirm natural name: {e}")
    return False

def upload_suspects(url: str, chat_engine):
    """
    Uploads suspect information to the database.
    """
    db = URLDatabase()
    try:
        prompt_key = "suspect_prompt"
        prompt_text = SHORT_PROMPTS[prompt_key]
        response_data = get_validated_response(prompt_key, prompt_text, SuspectResponse, chat_engine)
        if response_data is None:
            return
        if response_data.answer.lower() == "yes":
            url_id = db.get_url_id(url)
            suspects = response_data.evidence or []
            if not suspects:
                logger.info(f"No suspects found for URL: {url}")
                return
            for suspect in suspects:
                if confirm_natural_name(suspect):
                    try:
                        db.insert_suspect(url_id=url_id, suspect=suspect)
                        logger.info(f"Suspect inserted with natural name: {suspect}")
                    except DatabaseError as e:
                        logger.warning(f"Failed to insert suspect {suspect} for URL ID {url_id}: {e}")
                    try:
                        populate_suspect_forms_table(url, suspect, chat_engine)
                    except Exception as e:
                        logger.error(f"Failed to populate suspect form for {suspect}: {e}")
                else:
                    logger.info(f"Skipping suspect {suspect} as it is not a natural person's name.")
                time.sleep(random.uniform(1, 3))
    except Exception as e:
        logger.error(f"Failed to upload suspects: {e}")

def upload_victims(url: str, chat_engine):
    """
    Uploads victim information to the database.
    """
    db = URLDatabase()
    try:
        prompt_key = "victim_prompt"
        prompt_text = SHORT_PROMPTS[prompt_key]
        response_data = get_validated_response(prompt_key, prompt_text, VictimResponse, chat_engine)
        if response_data is None:
            return
        if response_data.answer.lower() == "yes":
            url_id = db.get_url_id(url)
            victims = response_data.evidence or []
            if not victims:
                logger.info(f"No victims found for URL: {url}")
                return
            for victim in victims:
                if confirm_natural_name(victim):
                    try:
                        db.insert_victim(url_id=url_id, victim=victim)
                        logger.info(f"Victim inserted with natural name: {victim}")
                    except DatabaseError as e:
                        logger.warning(f"Failed to insert victim {victim} for URL ID {url_id}: {e}")
                    try:
                        populate_victim_forms_table(url, victim, chat_engine)
                    except Exception as e:
                        logger.error(f"Failed to populate victim form for {victim}: {e}")
                else:
                    logger.info(f"Skipping victim {victim} as it is not a natural person's name.")
        else:
            logger.info(f"No victim found for URL: {url}")
    except Exception as e:
        logger.error(f"Failed to upload victims: {e}")

def populate_victim_forms_table(url: str, victim: str, chat_engine) -> None:
    """
    Populate the victim_forms table with details extracted from the text.
    """
    db = URLDatabase()
    try:
        victim_form_prompt = (
            f"Assistant, carefully extract the following details for the victim named {victim} from the text: "
            "1. Gender, 2. Date of Birth, 3. Age, 4. Address Notes, 5. Phone number, 6. Nationality, "
            "7. Occupation, 8. Victim Appearance, 9. Victim Vehicle Description, 10. Vehicle Plate #, "
            "11. Where is the victim been trafficked to?, 12. What job has the victim been offered? "
            "Return your answer in the following RAW JSON format ONLY and NO backticks or code blocks:\n"
            '{"gender": "male" or "female" or null,\n'
            '  "date_of_birth": "YYYY-MM-DD" or null,\n'
            '  "age": "integer" or null,\n'
            '  "address_notes": "text" or null,\n'
            '  "phone_number": "text" or null,\n'
            '  "nationality": "text" or null,\n'
            '  "occupation": "text" or null,\n'
            '  "appearance": "text" or null,\n'
            '  "vehicle_description": "text" or null,\n'
            '  "vehicle_plate_number": "text" or null,\n'
            '  "destination": "text" or null,\n'
            '  "job_offered": "text" or null\n'
            "}"
        )
        response_text = chat_engine.chat(victim_form_prompt)
        response_json = json.loads(response_text.response)
        response_json["name"] = victim
        response_data = VictimFormResponse.model_validate(response_json)
        logger.info(f"Extracted victim form data: {response_data}")
        if response_data:
            url_id = db.get_url_id(url)
            victim_id = db.get_victim_id(url_id, victim)
            if url_id is None:
                logger.error(f"URL not found in database: {url}")
                return
            db.insert_victim_form(url_id, response_data, victim_id)
            logger.info(f"Successfully inserted victim form for {victim}")
    except Exception as e:
        logger.error(f"Failed to populate victim_forms table for {victim} from URL '{url}': {e}")

def populate_suspect_forms_table(url: str, suspect: str, chat_engine) -> None:
    """
    Populate the suspect_forms table with details extracted from the text.
    """
    db = URLDatabase()
    try:
        suspect_form_prompt = (
            f"Assistant, carefully extract the following details for {suspect} from the text: "
            "1. Gender, 2. Date of Birth, 3. Age, 4. Address Notes, 5. Phone number, 6. Nationality, "
            "7. Occupation, 8. Role, 9. Suspect Appearance, 10. Suspect Vehicle Description, 11. Vehicle Plate #, "
            "12. What is evident of the suspect from the article, 13. Arrested status, 14. Arrest Date, "
            "15. Crime(s) Person Charged With, 16. Willing PV names, 17. Suspect in police custody, "
            "18. Suspect's current location, 19. Suspect's last known location, 20. Suspect's last known location date. "
            "Return your answer in the following RAW JSON format ONLY and NO backticks or code blocks:\n"
            '{"gender": "male" or "female" or null,\n'
            '  "date_of_birth": "YYYY-MM-DD" or null,\n'
            '  "age": "integer" or null,\n'
            '  "address_notes": "text" or null,\n'
            '  "phone_number": "text" or null,\n'
            '  "nationality": "text" or null,\n'
            '  "occupation": "text" or null,\n'
            '  "role": "text" or null,\n'
            '  "appearance": "text" or null,\n'
            '  "vehicle_description": "text" or null,\n'
            '  "vehicle_plate_number": "text" or null,\n'
            '  "evidence": "text" or null,\n'
            '  "arrested_status": "text" or null,\n'
            '  "arrest_date": "YYYY-MM-DD" or null,\n'
            '  "crimes_person_charged_with": "text" or null,\n'
            '  "willing_pv_names": "text" or null,\n'
            '  "suspect_in_police_custody": "text" or null,\n'
            '  "suspect_current_location": "text" or null,\n'
            '  "suspect_last_known_location": "text" or null,\n'
            '  "suspect_last_known_location_date": "YYYY-MM-DD" or null\n'
            "}"
        )
        response_text = chat_engine.chat(suspect_form_prompt)
        response_json = json.loads(response_text.response)
        response_json["name"] = suspect
        response_data = SuspectFormResponse.model_validate(response_json)
        logger.info(f"Extracted suspect form data: {response_data}")
        if response_data:
            url_id = db.get_url_id(url)
            suspect_id = db.get_suspect_id(url_id, suspect)
            if url_id is None:
                logger.error(f"URL not found in database: {url}")
                return
            db.insert_suspect_form(url_id, response_data, suspect_id)
            logger.info(f"Successfully inserted suspect form for {suspect}")
    except Exception as e:
        logger.error(f"Failed to populate suspect_forms table for {suspect} from URL '{url}': {e}")

# --- URL Processing (Synchronous) ---

def process_url(url: str, db: URLDatabase, driver) -> None:
    """
    Processes a single URL:
      - Checks accessibility
      - Attempts to load and extract text
      - Uses the chat engine to verify incidents and extract details
      - Inserts results into the database
    """
    if not is_url_accessible(url):
        logger.warning(f"URL not accessible: {url}")
        result = {
            "url": url,
            "domain_name": tldextract.extract(url).domain,
            "source": "google_search",
            "content": "",
            "actual_incident": -1,
            "accessible": 0
        }
        db.insert_url(result)
        return

    logger.info(f"Processing URL: {url}")
    domain_name = tldextract.extract(url).domain

    if not fetch_url_with_retries(driver, url):
        result = {
            "url": url,
            "domain_name": domain_name,
            "source": "google_search",
            "content": "",
            "actual_incident": -1,
            "accessible": 0
        }
        db.insert_url(result)
        return

    text = extract_main_text(url)
    if not text:
        logger.warning(f"No text extracted from URL: {url}")
        result = {
            "url": url,
            "domain_name": domain_name,
            "source": "google_search",
            "content": "",
            "actual_incident": -1,
            "accessible": 0
        }
        db.insert_url(result)
        return

    result = {
        "url": url,
        "domain_name": domain_name,
        "source": "google_search",
        "content": text,
        "actual_incident": -1,
        "accessible": 1
    }

    try:
        documents = [liDocument(text=text)]
        index = VectorStoreIndex.from_documents(documents)
        ChatMemoryBuffer.from_defaults(token_limit=3000).reset()
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            llm=OpenAI(temperature=0, model="o3-mini", request_timeout=120.0),
            memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
            system_prompt=(
                "You are a career forensic analyst with deep insight into crime and criminal activity, "
                "especially human trafficking. Your express goal is to investigate online reports and extract pertinent factual detail."
            )
        )
        incident_type, incidents = verify_incident(url, chat_engine)
        result.update(incident_type)
        db.insert_url(result)
        url_id = db.get_url_id(url)
        if result.get("actual_incident") == 1:
            for incident in incidents:
                db.insert_incident(url_id, incident)
                logger.info(f"Inserted incident: {incident}")
            upload_suspects(url, chat_engine)
            upload_victims(url, chat_engine)
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")

    time.sleep(random.uniform(1, 3))

# --- Main Execution ---

def main():
    db = URLDatabase()
    urls_from_files = get_unique_urls_from_csvs('output', 'url', 4, 1000)
    if pd.DataFrame(db.search_urls(limit=1000000)).empty:
        urls_from_db=[]
        logger.info("No urls in the db.")
    else:
        urls_from_db = pd.DataFrame(db.search_urls(limit=1000000))['url'].tolist()
        logger.info(f"{len(urls_from_db)} urls in the db.")
    urls = list(set(urls_from_files) - set(urls_from_db))
    logger.info(f"Found {len(urls)} new URLs to process.")
    driver = initialize_selenium()
    if driver is None:
        logger.critical("Selenium WebDriver initialization failed. Exiting.")
        return

    for url in urls:
        process_url(url, db, driver)

    driver.quit()
    logger.info("Google Miner service completed successfully.")

if __name__ == '__main__':
    main()
