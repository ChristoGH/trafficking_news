# Trafficking News Article Crawler

A Python script for discovering, collecting, and analyzing news articles related to human trafficking incidents, with particular focus on South African reporting.

## Overview

This module performs targeted searches for news articles covering trafficking-related incidents within a specified timeframe. It constructs search queries using selected keywords and filters, retrieves relevant URLs via Google search, and exports the results to a CSV file or Neo4j database for further analysis.

## Key Features

- **Intelligent Search Algorithm**: Combines trafficking-related terms with evidence keywords to create precise search queries
- **Temporal Analysis**: Configurable time-range filtering to focus on recent incidents
- **Domain Filtering**: Excludes unreliable or irrelevant sources
- **Geographic Focus**: Default targeting of South African news sources
- **Flexible Output Options**: Export to CSV or integrate with Neo4j graph database
- **Comprehensive Logging**: Detailed activity tracking and error handling

## Installation

### Prerequisites

- Python 3.11 or newer (3.13 recommended as specified in `pyproject.toml`)
- `uv` package manager (recommended for dependency management)
- Internet connection for performing searches

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone git@github.com:LoveJustice/lji_trafficking_news.git
   cd lji_trafficking_news
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   uv init
   uv venv --python=python3.11
   source .venv/bin/activate

   ```

3. **Install Required Dependencies**
   ```bash
   pip install -e .
   ```

4. **Set Up Custom Libraries**
   Ensure that the custom modules `libraries.google_search` and `libraries.neo4j_lib` are correctly set up in your project structure.

## Configuration

The crawler is configured using a JSON file (`search_config.json`) that should be placed in the current working directory.

### Sample Configuration

```json
{
  "run_configs": [
    {
      "id": "trafficking_search",
      "days_back": 7,
      "excluded_domains": [
        "example.com",
        "anotherdomain.com"
      ]
    }
  ]
}
```

### Configuration Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `id` | string | Unique identifier for the search configuration | "default_search" |
| `days_back` | integer | Number of days to look back from current date | 7 |
| `excluded_domains` | array | Domains to exclude from search results | `[]` |

## Usage

### Basic Execution

Run the script from the command line with an optional argument to specify the number of days to look back:

```bash
python web_crawler.py --days_back 7
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--days_back` | Override the number of days to look back | 7 |

## Script Workflow

1. **Configuration Loading**
   - Loads search parameters from `search_config.json`
   - Validates configuration integrity

2. **Search Construction**
   - Builds optimized Google search queries using:
     - Trafficking terms (e.g., "human trafficking", "child trafficking")
     - Evidence terms (e.g., "arrest", "rescue", "investigation")
     - News/article indicators
     - Geographic filters
     - Date range constraints
     - Domain exclusions

3. **Data Collection**
   - Executes search queries via `googlesearch` API
   - Filters results against excluded domains
   - Extracts domain information using `tldextract`

4. **Result Processing**
   - Saves valid URLs to timestamped CSV files
   - Optionally integrates with Neo4j database

## Data Storage

### CSV Output

Results are saved to CSV files with the naming pattern:
```
saved_urls_{search_id}_{timestamp}.csv
```

Each file contains the following columns:
- `url`: The complete article URL
- `domain_name`: Extracted domain of the source
- `source`: Set to 'google_miner'

### Neo4j Integration

When enabled, the crawler creates a graph representation with:
- URL nodes with properties:
  - `url`: The article URL
  - `source`: Set to 'google_miner'
- Domain nodes with properties:
  - `name`: Domain name
- Relationships:
  - `(URL)-[:HAS_DOMAIN]->(Domain)`

## Logging

The crawler maintains a detailed log file (`web_crawler.log`) that records:
- Script initialization and configuration
- Query construction details
- Search execution and results
- Data storage operations
- Errors and exceptions

## Dependencies

### Core Dependencies
- **libraries.google_search**: Custom module for performing Google searches
- **tldextract**: For reliable domain name extraction
- **libraries.neo4j_lib**: Custom module for Neo4j database integration (optional)

### Development Dependencies
- **pytest**: For test suite execution
- **black**: For code formatting
- **isort**: For import sorting
- **pylint**: For static code analysis

## Extending the Tool

### Adding New Search Terms

Modify the `TraffickingNewsSearch` class to include additional keywords:

```python
# Add or modify trafficking terms
self.trafficking_terms = [
    '"human trafficking"',
    '"cyber trafficking"',
    '"child trafficking"',
    '"forced labor"',
    '"sexual exploitation"',
    '"organ trafficking"',
    '"labor trafficking"',  # New term
    '"trafficking syndicate"'  # New term
]

# Add or modify evidence terms
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
    "testimony"  # New term
]
```

### Custom Output Methods

Create new output methods by extending the `TraffickingNewsSearch` class:

```python
def save_to_custom_database(self, urls: List[str]) -> None:
    """
    Save filtered articles to a custom database.
    """
    for url in urls:
        domain_name = tldextract.extract(url).domain
        # Your custom database logic here
        logger.info(f"Saved URL to custom database: {url}")
```

## Contributing

We welcome contributions to improve this tool. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

[Specify license information here]

## Developer

This tool was developed by **Christo Strydom** for Love Justice International's anti-trafficking initiatives. For technical inquiries, please contact the repository maintainers.

---

*Last updated: March 2025*