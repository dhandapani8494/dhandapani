#!/usr/bin/env python3
"""
Automation client:
- Load and validate JSON input
- Keep only entries with private=False
- POST result to service endpoint
- Print keys where 'valid' == True from response
"""

import json
import sys
import logging
from pathlib import Path
import requests

# Config
INPUT_FILE = "example.json"
SERVICE_URL = "https://example.com/service/generate"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

def load_json(filename: str):
    """Read and parse JSON file."""
    try:
        with open(filename, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logging.error("Input file not found: %s", filename)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error("Invalid JSON in %s: %s", filename, e)
        sys.exit(2)

def filter_non_private(data: dict):
    """Return dict entries with private=False."""
    if not isinstance(data, dict):
        logging.error("Expected a JSON object (dict) at root, got %s", type(data))
        sys.exit(3)

    result = {k: v for k, v in data.items() if isinstance(v, dict) and v.get("private") is False}
    logging.info("Selected %d non-private entries from %d total", len(result), len(data))
    return result

def post_json(payload: dict):
    """Send JSON via POST to service."""
    try:
        resp = requests.post(SERVICE_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error("HTTP request failed: %s", e)
        sys.exit(4)
    except json.JSONDecodeError:
        logging.error("Service returned invalid JSON")
        sys.exit(5)

def print_valid_keys(response: dict):
    """Print keys with child 'valid'=true."""
    if not isinstance(response, dict):
        logging.error("Expected dict in service response")
        sys.exit(6)

    for key, value in response.items():
        if isinstance(value, dict) and value.get("valid") is True:
            print(key)

def main():
    data = load_json(INPUT_FILE)
    filtered = filter_non_private(data)
    response = post_json(filtered)
    print_valid_keys(response)

if _name_ == "_main_":
    main()
