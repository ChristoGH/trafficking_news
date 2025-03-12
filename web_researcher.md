Below is an example of a detailed **README.md** that explains the purpose, setup, and usage of the project. It also highlights the custom modules that must be included.

---

# Trafficking News Research

A Python-based tool designed to search for, extract, and process news articles related to human trafficking incidents. 
The tool leverages multiple extraction methods (e.g., newspaper3k, readability-lxml, Selenium) to retrieve article 
content and uses a custom chat engine (powered by LLMs) to verify and extract pertinent details about trafficking 
incidents, suspects, and victims.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Custom Modules](#custom-modules)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Multi-Method Article Extraction:**  
  Uses newspaper3k, requests with readability-lxml, and Selenium as fallbacks to extract the main text from an article URL.

- **Google Custom Search Integration:**  
  Fetches targeted news articles using the Google Custom Search API.

- **Dynamic Content Handling:**  
  Renders JavaScript-driven pages with Selenium to ensure that dynamic content is processed correctly.

- **Chat Engine Verification:**  
  Uses a chat engine with custom prompts to determine if an article reports an actual trafficking incident and to extract additional details about suspects and victims.

- **Database Integration:**  
  Stores URLs and extracted information (including incidents, suspect data, and victim data) in a local database.

- **Detailed Logging:**  
  Logs key steps and errors to `google_search.log` for traceability and debugging.

## Requirements

### External Python Packages

Ensure you have Python 3.x installed along with the following packages:

- `pandas`
- `requests`
- `tldextract`
- `beautifulsoup4` (bs4)
- `readability-lxml`
- `newspaper3k`
- `google-api-python-client`
- `selenium`
- `llama_index`
- Standard libraries: `os`, `json`, `math`, `random`, `time`, `logging`, `typing`

You can install the necessary packages via pip:

```bash
pip install pandas requests tldextract beautifulsoup4 readability-lxml newspaper3k google-api-python-client selenium llama_index
```

### Custom Modules

The project depends on the following custom modules which **must be included in your project directory or accessible via your PYTHONPATH**:

- **`work_with_db.py`**  
  Provides the `URLDatabase` class and `DatabaseError` for managing database operations.

- **`trafficking_news.py`**  
  Contains the `TraffickingNewsSearch` class and a helper function `extract_main_text_selenium` for custom trafficking news search functionality.

- **`models.py`**  
  Defines data models for validating responses, including:
  - `ConfirmResponse`
  - `IncidentResponse`
  - `SuspectFormResponse`
  - `SuspectResponse`
  - `VictimResponse`
  - `VictimFormResponse`

- **`get_urls_from_csvs.py`**  
  Provides the `get_unique_urls_from_csvs` function, which extracts unique URLs from CSV files.

## Installation

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Set Up a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   *(If a `requirements.txt` file is not available, manually install the packages listed above.)*

4. **Ensure Custom Modules Are Available**

   Make sure the custom files (`work_with_db.py`, `trafficking_news.py`, `models.py`, and `get_urls_from_csvs.py`) are in your project directory or are accessible in your PYTHONPATH.

## Configuration

### Environment Variables

The script requires the following environment variables for the Google Custom Search API:

- **`GOOGLE_API_KEY`**: Your Google API key.
- **`GOOGLE_CSE_ID`**: Your Google Custom Search Engine ID.

You can set these in your shell or use a `.env` file (with a tool like `python-dotenv`) to manage environment variables.

### Selenium WebDriver

The script uses Selenium with Chrome. Verify that:

- **ChromeDriver** is installed.
- The path to the ChromeDriver (default is set to `/opt/homebrew/bin/chromedriver`) is correct for your system. Update the `driver_path` in the code if necessary.

### Logging

Logs are written to `google_search.log`. Ensure the directory has appropriate write permissions.

## Usage

Run the script from the command line:

```bash
python web_researcher.py --days_back 7
```

> **Note:** The `--days_back` parameter is mentioned in the module docstring; however, the main function currently does not parse this argument. You may need to update the code to handle command-line arguments if required.

The script performs the following:

1. Reads unique URLs from CSV files using `get_urls_from_csvs`.
2. Filters out URLs already stored in the database via `URLDatabase`.
3. Processes each URL by:
   - Checking accessibility (using Selenium).
   - Extracting article text using multiple methods.
   - Verifying if the article reports a trafficking incident using a custom chat engine.
   - Uploading suspect and victim details to the database.
4. Logs each step to help diagnose issues.

## Project Structure

```plaintext
├── web_researcher.py         # Main script
├── work_with_db.py           # Custom module for database interactions
├── trafficking_news.py       # Custom module for trafficking news searches
├── models.py                 # Custom module for response models
├── get_urls_from_csvs.py     # Custom module for extracting URLs from CSV files
├── requirements.txt          # (Optional) List of Python dependencies
└── google_search.log         # Log file for application events
```

## Custom Modules

The following are custom modules used in the project:

- **`work_with_db.py`**  
  Manages database operations including URL insertion and updates.

- **`trafficking_news.py`**  
  Provides functionality to search for trafficking-related news and includes helper functions for Selenium-based extraction.

- **`models.py`**  
  Contains data models (e.g., `IncidentResponse`, `SuspectFormResponse`, etc.) used for validating JSON responses from the chat engine.

- **`get_urls_from_csvs.py`**  
  Contains the helper function `get_unique_urls_from_csvs` that extracts unique URLs from CSV files.

## Contributing

Contributions and suggestions are welcome. Please submit a pull request or open an issue if you have any improvements or bug fixes.

## License

*(Include your license information here.)*

## Contact

For any inquiries or further assistance, please contact:

**Christo Strydom**

---

