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
