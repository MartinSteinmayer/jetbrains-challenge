import re
import requests
from bs4 import BeautifulSoup

# Checks if the given code is in markdown format and trims out the delimiters, including the language name.
def trim_md(code: str) -> str:
    if code.startswith("```"):
        first_newline_idx = code.find("\n")

        if first_newline_idx != -1:
            code = code[first_newline_idx + 1:]

        if code.endswith("```"):
            code = code[:-3]

    return code.strip()


# Cleans up docker logs
def clean_logs(logs: str) -> str:
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1b\[([0-9]{1,2}(?:;[0-9]{1,2})*)?[m|K]')
    cleaned_logs = re.sub(ansi_escape, '', logs)

    # Normalize newlines
    cleaned_logs = cleaned_logs.replace("\r\n", "\n").replace("\r", "\n")

    return cleaned_logs.strip()  # Remove leading/trailing whitespace


# Cleans up logs from pylint
def format_pylint_output(raw_logs: str) -> str:
    """
    Converts raw pylint logs into a more human-readable format.
    """
    lines = raw_logs.strip().splitlines()
    formatted_output = []

    for line in lines:
        if line.startswith("************* Module"):
            formatted_output.append(f"\nModule: {line.split()[-1]}")
        elif line.startswith("/") and ":" in line:
            # Extract file, line, column, and error message
            parts = line.split(":")
            file_path = parts[0]
            line_number = parts[1]
            column_number = parts[2]
            error_message = ":".join(parts[3:]).strip()
            formatted_output.append(
                f"File: {file_path}, Line: {line_number}, Column: {column_number}\n  -> {error_message}"
            )
        elif "Your code has been rated" in line:
            formatted_output.append(f"\n{line}")
        else:
            formatted_output.append(line)

    return "\n".join(formatted_output)


# Parsing/trimming of html
def extract_webpage_content(url: str) -> str:
    """
    Extract meaningful content from a webpage using Beautiful Soup.

    Args:
        url (str): The URL of the webpage.

    Returns:
        str: Extracted content, specifically tailored for JetBrains, StackOverflow, GeeksforGeeks, and intellij-support.jetbrains.com.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch the webpage: {str(e)}")

    # Parse the webpage using Beautiful Soup
    soup = BeautifulSoup(response.content, "html.parser")

    # Special handling for intellij-support.jetbrains.com
    if "intellij-support.jetbrains.com" in url:
        try:
            title = soup.find("h1").get_text(strip=True)
            content_area = soup.find("div", class_=re.compile(r"content|article", re.IGNORECASE))
            paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
            content_paragraphs = [p.get_text(" ", strip=True) for p in paragraphs]
            return f"**{title}**\n\n" + "\n\n".join(content_paragraphs)
        except Exception:
            return None  # Return None if extraction fails

    # Special handling for JetBrains
    if "jetbrains.com" in url:
        try:
            title = soup.find("h1").get_text(strip=True)
            content_area = soup.find("div", class_=re.compile(r"(main|content|doc-content)", re.IGNORECASE))
            paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
            content_paragraphs = [p.get_text(" ", strip=True) for p in paragraphs]
            return f"**{title}**\n\n" + "\n\n".join(content_paragraphs)
        except Exception:
            return None

    # Special handling for StackOverflow
    if "stackoverflow.com" in url:
        try:
            question_title = soup.find("a", class_="question-hyperlink").get_text(strip=True)
            question_body = soup.find("div", class_="s-prose js-post-body").get_text(" ", strip=True)
            first_answer = soup.find_all("div", class_="s-prose js-post-body")[1].get_text(" ", strip=True)
            return f"**Question:**\n{question_title}\n\n**Question Text:**\n{question_body}\n\n**First Answer:**\n{first_answer}"
        except (AttributeError, IndexError):
            return None

    # Special handling for GeeksforGeeks
    if "geeksforgeeks.org" in url:
        try:
            title = soup.find("h1").get_text(strip=True)
            content_area = soup.find("div", class_=re.compile(r"content|article", re.IGNORECASE))
            paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
            content_paragraphs = [p.get_text(" ", strip=True) for p in paragraphs]
            return f"**{title}**\n\n" + "\n\n".join(content_paragraphs)
        except Exception:
            return None

    # General content extraction for non-specific domains
    content_areas = soup.find_all(
        ["main", "article", "div", "section"],
        attrs={
            "id": re.compile(r"content|main|article-body", re.IGNORECASE),
            "class": re.compile(r"content|post|text|article-body", re.IGNORECASE),
        },
    )
    if content_areas:
        paragraphs = [area.get_text(" ", strip=True) for area in content_areas]
        return "\n\n".join(paragraphs)
    return None