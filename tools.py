"""
This file contains the tools that will be used in the LLM.
"""

# General imports
import requests

# Langchain
from langchain_core.tools import tool


@tool
def search(query: str):
    """Call to surf the web."""
    # This is a placeholder, but don't tell the LLM that...
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


# Define the Bing Search Tool
@tool
def bing_search(query: str, count: int = 3) -> str:
    """
    Perform a web search using Azure Bing Search API.

    This function performs a web search using the Azure Bing Search API. 
    It is designed to handle queries specifically related to JetBrains tools, 
    such as PyCharm and IntelliJ.

    Args:
        query (str): The search query string.
        count (int, optional): The number of search results to return. Defaults to 3.

    Returns:
        str: A formatted string of the top search results, including title, snippet, and URL.
        If no results are found or an error occurs, an appropriate error message is returned.

    Raises:
        requests.RequestException: If the HTTP request fails or the Bing API endpoint is unreachable.
    """
    print("entered")
    bing_endpoint = "https://api.bing.microsoft.com/v7.0/search"
    bing_api_key = "636db1aa1d4c4169b1b365d0514940f4"  # Replace with your Bing API Key

    headers = {"Ocp-Apim-Subscription-Key": bing_api_key}
    params = {"q": query, "count": count}

    try:
        response = requests.get(bing_endpoint, headers=headers, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    except requests.RequestException as e:
        return f"Failed to perform web search: {str(e)}"

    # Parse the results
    results = response.json().get("webPages", {}).get("value", [])
    if not results:
        return "No results found."

    # Format and return the top results
    formatted_results = "\n\n".join(
        [f"Title: {result['name']}\nSnippet: {result['snippet']}\nLink: {result['url']}" for result in results])
    print(formatted_results)
    return formatted_results
