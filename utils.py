"""
Checks if the given code is in markdown format and trims out the delimiters, including the language name.
"""


def trimMd(code: str) -> str:
    if code.startswith("```"):
        first_newline_idx = code.find("\n")

        if first_newline_idx != -1:
            code = code[first_newline_idx + 1:]

        if code.endswith("```"):
            code = code[:-3]

    return code.strip()

