import os
from pathlib import Path
import pyperclip


def write_directory_to_clipboard(dir_path, ignore_dirs=None):

    if ignore_dirs is None:
        ignore_dirs = []

    output = []

    output.append(
        "This is my directory. The files are separated into folders when necessary. Give your answer considering the structure of the project."
    )

    for root, dirs, files in os.walk(dir_path):
        # Check if the current directory should be ignored
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        # Get the depth of the directory to make a tree structure
        level = root.replace(str(dir_path), '').count(os.sep)
        indent = ' ' * 4 * level
        output.append(f"{indent}{Path(root).name}/")
        sub_indent = ' ' * 4 * (level + 1)

        # Write each file's content
        for file_name in files:
            file_path = Path(root) / file_name
            output.append(f"{sub_indent}{file_name}")
            output.append(f"{sub_indent}{'-'*20}")  # Divider for clarity
            try:
                with open(file_path, 'r') as file_content:
                    output.append(file_content.read())
            except Exception as e:
                output.append(f"{sub_indent}Error reading file: {e}")
            output.append(f"{sub_indent}{'-'*20}\n")  # End of file marker

    # Copy the output to the clipboard
    pyperclip.copy('\n'.join(output))
    print("Directory structure and content copied to clipboard.")


# Usage example
dir_path = Path('./')  # Replace with your directory path
ignore_dirs = ['lib', 'node_modules', 'pack', 'venv', '.idea', '.run',
               'gradle']  # Add any directories you want to ignore
write_directory_to_clipboard(dir_path, ignore_dirs)
