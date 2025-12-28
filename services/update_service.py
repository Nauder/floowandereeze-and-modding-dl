"""
This module provides functionality to update the database with the latest data from the remote
source.
"""

import pandas as pd
import requests
from requests.exceptions import RequestException, Timeout, HTTPError
from pandas import read_parquet, DataFrame
from pandas.errors import EmptyDataError

from database.models import SleeveModel, CardModel, FieldModel
from database.objects import session


def get_github_raw_file(
    path: str, owner="Nauder", repo="floowandereeze-and-modding-etl-dl"
) -> str:
    """
    Fetch a raw file from a private GitHub repository using GitHub REST API.

    :param owner: GitHub username or organization name that owns the repository.
    :param repo: Repository name.
    :param path: Path to the file in the repository.

    :return: The raw content of the file.
    :raises HTTPError: If the GitHub API request fails
    :raises Timeout: If the request times out
    :raises RequestException: For other request-related errors
    :raises ValueError: If the response doesn't contain a download URL
    """
    # GitHub API URL for repository contents
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    # Headers for authentication
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        # Send a GET request to fetch file metadata
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses

        file_data = response.json()

        # Extract the download URL from the response
        if "download_url" not in file_data:
            raise ValueError("No download URL found in the response.")

        raw_url = file_data["download_url"]

        # Send a second GET request to fetch the raw file content
        raw_response = requests.get(raw_url, headers=headers, timeout=10)
        raw_response.raise_for_status()

        return raw_response.text

    except Timeout as e:
        raise Timeout(f"Request timed out: {str(e)}") from e
    except HTTPError as e:
        raise HTTPError(f"GitHub API request failed: {str(e)}") from e
    except RequestException as e:
        raise RequestException(f"Request failed: {str(e)}") from e


def get_github_parquet_file(
    path: str, owner="Nauder", repo="floowandereeze-and-modding-etl-dl"
) -> DataFrame:
    """
    Fetch a raw file from a private GitHub repository using GitHub REST API.

    :param owner: GitHub username or organization name that owns the repository.
    :param repo: Repository name.
    :param path: Path to the file in the repository.

    :return: The raw content of the file as a pandas DataFrame.
    :raises HTTPError: If the GitHub API request fails
    :raises Timeout: If the request times out
    :raises RequestException: For other request-related errors
    :raises ValueError: If the response doesn't contain a download URL
    :raises EmptyDataError: If the parquet file is empty or invalid
    """
    # GitHub API URL for repository contents
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    # Headers for authentication
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        # Send a GET request to fetch file metadata
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        file_data = response.json()

        # Extract the download URL from the response
        if "download_url" not in file_data:
            raise ValueError("No download URL found in the response.")

        raw_url = file_data["download_url"]

        return read_parquet(raw_url)

    except Timeout as e:
        raise Timeout(f"Request timed out: {str(e)}") from e
    except HTTPError as e:
        raise HTTPError(f"GitHub API request failed: {str(e)}") from e
    except RequestException as e:
        raise RequestException(f"Request failed: {str(e)}") from e
    except EmptyDataError as e:
        raise EmptyDataError(f"Failed to read parquet file: {str(e)}") from e


def update_sleeves() -> None:
    """
    Updates the sleeves in the database by completely replacing all existing sleeves
    with the latest data from the remote source.

    This function:
    1. Fetches the latest sleeves data from the remote parquet file
    2. Deletes all existing sleeves from the database
    3. Adds all sleeves from the remote data
    """
    remote_sleeves = get_github_parquet_file("data/sleeves.parquet")
    session.query(SleeveModel).delete()
    session.add_all(
        [
            SleeveModel(
                medium_bundle=sleeve["medium"],
                small_bundle=sleeve["small"],
            )
            for _, sleeve in remote_sleeves.iterrows()
            if not pd.isnull(sleeve["medium"]) and not pd.isnull(sleeve["small"])
        ]
    )


def update_cards() -> None:
    """
    Updates the cards in the database by completely replacing all existing cards
    with the latest data from the remote source.

    This function:
    1. Fetches the latest cards data from the remote parquet file
    2. Deletes all existing cards from the database
    3. Adds all cards from the remote data with their bundle, name, description, and data_index
    """
    remote_cards = get_github_parquet_file("data/cards.parquet")
    session.query(CardModel).delete()
    session.add_all(
        [
            CardModel(
                name=card["name"],
                large_bundle=card["large"],
                medium_bundle=card["medium"],
                small_bundle=card["small"],
            )
            for _, card in remote_cards.iterrows()
        ]
    )


def update_fields() -> None:
    """
    Updates the fields in the database by completely replacing all existing fields
    with the latest data from the remote source.

    This function:
    1. Fetches the latest fields data from the remote parquet file
    2. Deletes all existing fields from the database
    3. Adds all fields from the remote data with their bundle, flipped, and bottom properties
    """
    remote_fields = get_github_parquet_file("data/fields.parquet")
    session.query(FieldModel).delete()
    session.add_all(
        [
            FieldModel(
                medium_bundle=field["medium"],
                small_bundle=field["small"],
            )
            for _, field in remote_fields.iterrows()
            if not pd.isnull(field["medium"]) and not pd.isnull(field["small"])
        ]
    )
