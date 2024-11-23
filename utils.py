import re


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

