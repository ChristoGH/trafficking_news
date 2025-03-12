#!/usr/bin/env python3
"""
Module for targeted news article search and filtering related to trafficking incidents.

Usage:
    python web_crawler.py --days_back 7

Developer: Christo Strydom
"""

import csv
import argparse
import logging
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urlparse
import tldextract
  # Ensure you are using the correct googlesearch package.
from googlesearch import search
import json
# from libraries.google_search import search
import os

from libraries.neo4j_lib import execute_neo4j_query
from googlesearch import search
print(f"Search function being used: {search}")
print(f"Search function module: {search.__module__}")

# Add this temporary code to webcrawler.py to inspect the function
import inspect
from googlesearch import search
print("Search function signature:")
print(inspect.signature(search))
print("Search function source location:")
print(inspect.getfile(search))
import inspect
from googlesearch import search
print("Working project:")
print(f"Search function: {search}")
print(f"Search function module: {search.__module__}")
print(f"Search function location: {inspect.getfile(search)}")
print(f"Search function signature: {inspect.signature(search)}")
# ------------------------------
# Configuration Loading & Logger Setup
# ------------------------------
def load_config(config_path: str) -> dict:
    """
    Load configuration from a JSON file.
    """
    full_path = os.path.join(os.getcwd(), config_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Configuration file not found: {full_path}")
    try:
        with open(full_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file: {str(e)}", e.doc, e.pos)

config = load_config("search_config.json")

logging.basicConfig(
    filename="web_crawler.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logger.info("Google Miner service started (refactored, sync version).")


# ------------------------------
# TraffickingNewsSearch Class Definition
# ------------------------------
class TraffickingNewsSearch:
    """
    Encapsulates news article search logic related to trafficking incidents.
    """
    def __init__(self, search_config: dict) -> None:
        self.search_name = search_config.get('id', 'default_search')
        self.days_back = search_config.get('days_back', 7)
        # Optional filtering: these can be provided via configuration; otherwise default to empty lists.
        self.excluded_domains = search_config.get('excluded_domains', [])
        self.trafficking_terms = [
            '"human trafficking"',
            '"cyber trafficking"',
            '"child trafficking"',
            '"forced labor"',
            '"sexual exploitation"',
            '"organ trafficking"',
        ]
        self.evidence_terms = [
            "arrest",
            "suspect",
            "victim",
            "rescue",
            "operation",
            "investigation",
            "prosecute",
            "charged",
            "convicted",
        ]

    def is_valid_news_domain(self, url: str) -> bool:
        """
        Returns True if the URL does not belong to an excluded domain.
        """
        try:
            domain = urlparse(url).netloc.lower()
            # Exclude if any excluded domain appears in the URL's domain.
            if any(excluded in domain for excluded in self.excluded_domains):
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking domain validity for {url}: {e}")
            return False

    def construct_query(self, start_date: str, end_date: str, include_evidence_terms: bool = True) -> str:
        """
        Construct a targeted search query.
        """
        trafficking_part = f"({' OR '.join(self.trafficking_terms)})"
        if include_evidence_terms:
            evidence_part = f"({' OR '.join(self.evidence_terms)})"
            base_query = f'{trafficking_part} AND {evidence_part} AND ("news" OR "article") AND "South Africa"'
        else:
            base_query = trafficking_part

        excluded_sites = " ".join([f"-site:{domain}" for domain in self.excluded_domains])
        final_query = f"{base_query} {excluded_sites} after:{start_date} before:{end_date}"
        logger.debug(f"Constructed query: {final_query}")
        return final_query

    def fetch_articles(self, query: str, max_results: int = 200) -> List[str]:
        """
        Fetch articles synchronously using google search.
        """
        articles = []
        try:
            # Using parameters that match the function signature in trafficking_news
            for url in search(
                    term=query,
                    num_results=max_results,
                    lang="en",
                    sleep_interval=2  # equivalent to pause
            ):
                if self.is_valid_news_domain(url):
                    articles.append(url)
            return articles
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []

    def get_recent_articles(self) -> List[str]:
        """
        Retrieve recent articles based on days_back.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days_back)
        query = self.construct_query(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        logger.info(f"Searching for articles with query: {query}")
        return self.fetch_articles(query)

    def save_to_neo4j(self, urls: List[str]) -> None:
        """
        Save filtered articles to a Neo4j database.
        """
        query = """
            MERGE (url:Url {url: $url, source: 'google_miner'})
            WITH url
            MERGE (domain:Domain { name: $domain_name })
            MERGE (url)-[:HAS_DOMAIN]->(domain)
        """
        for url in urls:
            domain_name = tldextract.extract(url).domain
            parameters = {"domain_name": domain_name, "url": url}
            execute_neo4j_query(query, parameters)
            logger.info(f"Saved URL to Neo4j: {url}")

    def save_to_csv(self, urls: List[str]) -> None:
        """
        Save filtered articles to a CSV file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"{output_dir}/saved_urls_{self.search_name}_{timestamp}.csv"
        with open(file_name, mode="w", newline="", encoding="utf-8") as csv_file:
            fieldnames = ["url", "domain_name", "source"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for url in urls:
                domain_name = tldextract.extract(url).domain
                writer.writerow({
                    "url": url,
                    "domain_name": domain_name,
                    "source": "google_miner"
                })
                logger.info(f"Saved URL to CSV: {url}")
        logger.info(f"CSV file '{file_name}' created successfully.")


# ------------------------------
# Main Entry Point (Synchronous)
# ------------------------------
def main() -> None:
    """
    Execute searches and save articles.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--days_back", type=int, help="Number of days to search back.", default=7)
    args = parser.parse_args()

    # Process each search configuration.
    for search_config in config.get('run_configs', []):
        # Use the days_back value provided from the command-line.
        search_config['days_back'] = args.days_back

        searcher = TraffickingNewsSearch(search_config)
        articles = searcher.get_recent_articles()

        logger.info(f"Retrieved {len(articles)} articles in the past {search_config['days_back']} day(s).")
        if not articles:
            logger.info("No articles found for this configuration.")
            continue

        for article in articles:
            logger.info(f"Found article: {article}")

        # Uncomment the next line to store results in Neo4j:
        # searcher.save_to_neo4j(articles)
        searcher.save_to_csv(articles)

if __name__ == "__main__":
    main()
