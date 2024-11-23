"""
This file contains the tools that will be used in the LLM.
"""

# General imports
import requests
import docker
import uuid
import tempfile
import docker.utils

from urllib.parse import urlparse
from utils import trim_md, clean_logs, format_pylint_output, extract_webpage_content

# Langchain
from langchain_core.tools import tool

# Python error check
@tool
def run_python_docker(code: str) -> dict:
    """
    Runs Python code insider a docker container and returns the output or errors.

    Args:
        code (str) : Python code to execute.
    
    Returns:
        dict: Contains "success" (bool), "output" (str) and "error" (str).
    """

    # Remove the markdown delimiters from the given code string
    code = trim_md(code)

    print("\n\nPYTHON\n\n")

    # Initializer docker client
    client = docker.from_env()

    try:
        # Create a temporary container with the python image
        container = client.containers.run(image="tomassoares/jetbrains-cleaner-tool:latest",
                                          command=f"python3 -c '{code}'",
                                          detach=True,
                                          stdin_open=True,
                                          tty=True)

        # Wait for the container to finish
        exit_status = container.wait()["StatusCode"]
        raw_logs = container.logs().decode("utf-8")
        logs = clean_logs(raw_logs)

        # Clean up container
        container.remove()

        if exit_status == 0:
            return {"success": True, "output": logs, "error": None}
        else:
            return {"success": False, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# Python linter
@tool
def lint_python_docker(code: str) -> dict:

    """
    Lint the provided Python code using pylint inside a Docker container.

    Args:
        code (str): A string containing the Python code to be linted.

    Returns:
        dict: Contains "success" (bool), "output" (str), and "error" (str).
        
    """

    client = docker.from_env()
    container_image = "tomassoares/jetbrains-cleaner-tool:latest"

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".py") as temp_file:
            temp_file.write(code)
            temp_file.close()

            container_code_path = f"/tmp/{uuid.uuid4().hex}.py"
            command = f"pylint {container_code_path}"

            container = client.containers.run(
                image=container_image,
                command=command,
                volumes={temp_file.name: {"bind": container_code_path, "mode": "ro"}},
                detach=True,
                tty=True,
                stdin_open=True,
            )

            exit_status = container.wait()["StatusCode"]
            raw_logs = container.logs().decode("utf-8")

            container.remove()

            # Parse pylint logs for human-readable output
            human_readable_output = format_pylint_output(raw_logs)

            # Set success based on exit code
            if exit_status == 0:
                return {"success" : True, "output": human_readable_output, "error": None}
            else:
                return {"success" : False, "output": None, "error": human_readable_output}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# C sanitizer
@tool
def clean_c_docker(code: str, params: list) -> dict:
    """
    Compiles C code in docker container and runs valgrind + fsanitize to report potential leaks.

    Args:
        code (str): The C source code to compile and sanitize using leak sanitizer and valgrind.
        params (list): A list of strings representing the parameters that are given to the c code to run.

    Returns:
        dict: Contains the success flag, sanitize (valgrind+fsaniitze) output, and any errors.
    """

    # Remove the markdown delimiters from the given code string
    code = trim_md(code)
    try:
        client = docker.from_env()
        # Create a unique filename for the C source code file and the executable
        source_filename = f"/tmp/{uuid.uuid4().hex}.c"
        executable_filename_asan = f"/tmp/{uuid.uuid4().hex}_asan"
        executable_filename_valgrind = f"/tmp/{uuid.uuid4().hex}_valgrind"

        # Create a temporary container with the C image
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file.close()

            # Docker run command
            command = (
                f"sh -c 'gcc {source_filename} -o {executable_filename_asan} "
                f"-fsanitize=address,undefined -static-libasan && "
                f"./{executable_filename_asan} {' '.join(params)} && "
                f"gcc {source_filename} -o {executable_filename_valgrind} && "
                f"valgrind --leak-check=full --track-origins=yes ./{executable_filename_valgrind} {' '.join(params)}'"
            )

            container = client.containers.run(image="tomassoares/jetbrains-cleaner-tool",
                                              command=command,
                                              volumes={temp_file.name: {
                                                  'bind': f'{source_filename}',
                                                  'mode': 'ro'
                                              }},
                                              detach=True,
                                              tty=True,
                                              stdin_open=True)

            # Wait for the code to finish and get the exit status code and logs
            exit_status = container.wait()["StatusCode"]
            raw_logs = container.logs().decode("utf-8")
            logs = clean_logs(raw_logs)

            # Cleanup container
            container.remove()

            if exit_status == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": False, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# C linter
@tool
def lint_c_docker(code: str) -> dict:
    """
    Lints C code in docker container with clang-tidy, clang-format and cppcheck to enforce code style.

    Args:
        code (str): The C source code to lint.

    Returns:
        dict: Contains the success flag, linting output, and any errors.
    """

    # Remove the markdown delimiters from the given code string
    code = trim_md(code)

    try:
        client = docker.from_env()

        source_filename = f"/tmp/{uuid.uuid4().hex}.c"

        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file.close()

            # Command to lint the code using clang-tidy
            command = (
                f"sh -c 'clang-tidy {source_filename} -- && "
                f"clang-format -i {source_filename} && "
                f"cppcheck {source_filename}'"    
            )

            container = client.containers.run(image="tomassoares/jetbrains-cleaner-tool:latest",
                                              command=command,
                                              volumes={temp_file.name: {
                                                  'bind': f'{source_filename}',
                                                  'mode': 'ro'
                                              }},
                                              detach=True,
                                              tty=True,
                                              stdin_open=True)

            # Wair for linting to complete
            exit_status = container.wait()["StatusCode"]
            raw_logs = container.logs().decode('utf-8')
            logs = clean_logs(raw_logs)

            # Cleanup container
            container.remove()

            if exit_status == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": True, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# C++ sanitizer
@tool
def clean_cpp_docker(code: str, params: list) -> dict:
    """
    Compiles C++ code in docker container and runs valgrind + fsanitize to report potential leaks.

    Args:
        code (str): The C++ source code to compile and sanitize using leak sanitizer and valgrind.
        params (list): A list of strings representing the parameters that are given to the C++ code to run.

    Returns:
        dict: Contains the success flag, sanitize (valgrind+fsaniitze) output, and any errors.
    """
    # Remove the markdown delimiters from the given code string
    code = trim_md(code)
    try:
        client = docker.from_env()
        # Create a unique filename for the C source code file and the executable
        source_filename = f"/tmp/{uuid.uuid4().hex}.c"
        executable_filename_asan = f"/tmp/{uuid.uuid4().hex}_asan"
        executable_filename_valgrind = f"/tmp/{uuid.uuid4().hex}_valgrind"

        # Create a temporary container with the C image
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file.close()

            # Docker run command
            command = (
                f"sh -c 'g++ {source_filename} -o {executable_filename_asan} "
                f"-fsanitize=address,undefined -static-libasan && "
                f"./{executable_filename_asan} {' '.join(params)} && "
                f"g++ {source_filename} -o {executable_filename_valgrind} && "
                f"valgrind --leak-check=full --track-origins=yes ./{executable_filename_valgrind} {' '.join(params)}'"
            )

            container = client.containers.run(image="tomassoares/jetbrains-cleaner-tool",
                                            command=command,
                                            volumes={temp_file.name: {
                                                'bind': f'{source_filename}',
                                                'mode': 'ro'
                                            }},
                                            detach=True,
                                            tty=True,
                                            stdin_open=True)

            # Wait for the code to finish and get the exit status code and logs
            exit_status = container.wait()["StatusCode"]
            raw_logs = container.logs().decode("utf-8")
            logs = clean_logs(raw_logs)

            # Cleanup container
            container.remove()

            if exit_status == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": False, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# C++ linter
@tool
def lint_cpp_docker(code: str) -> dict:
    """
    Lints C++ code in docker container with clang-tidy, clang-format and cppcheck to enforce code style.

    Args:
        code (str): The C++ source code to lint.

    Returns:
        dict: Contains the success flag, linting output, and any errors.
    """

    # Remove the markdown delimiters from the given code string
    code = trim_md(code)

    try:
        client = docker.from_env()

        source_filename = f"/tmp/{uuid.uuid4().hex}.c"

        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file.close()

            # Command to lint the code using clang-tidy
            command = (
                f"sh -c 'clang-tidy {source_filename} -- && "
                f"clang-format -i {source_filename} && "
                f"cppcheck {source_filename}'"    
            )

            container = client.containers.run(image="tomassoares/jetbrains-cleaner-tool:latest",
                                              command=command,
                                              volumes={temp_file.name: {
                                                  'bind': f'{source_filename}',
                                                  'mode': 'ro'
                                              }},
                                              detach=True,
                                              tty=True,
                                              stdin_open=True)

            # Wair for linting to complete
            exit_status = container.wait()["StatusCode"]
            raw_logs = container.logs().decode('utf-8')
            logs = clean_logs(raw_logs)

            # Cleanup container
            container.remove()

            if exit_status == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": True, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# Bing search for allowed webpages 
@tool
def bing_search(query: str, count: int = 3) -> str:
    """
    Perform a web search using Azure Bing Search API and extract meaningful content from the results.

    Args:
        query (str): The search query string.
        count (int, optional): The number of search results to return. Defaults to 3.

    Returns:
        str: A formatted string of the top search results from specific domains, including titles and content in paragraphs.
        If no results are found or an error occurs, an appropriate error message is returned.
    """
    bing_api_key = "636db1aa1d4c4169b1b365d0514940f4"  # Replace with your Bing API key
    bing_endpoint = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": bing_api_key}
    params = {"q": query, "count": count}

    # Allowed domains
    allowed_domains = ["stackoverflow.com", "geeksforgeeks.org", "jetbrains.com"]

    try:
        # Perform the Bing search
        response = requests.get(bing_endpoint, headers=headers, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Failed to perform web search: {str(e)}"

    # Parse the Bing search results
    results = response.json().get("webPages", {}).get("value", [])
    if not results:
        return "No results found."

    # Process and extract content from each result
    formatted_results = []
    for result in results:
        title = result.get("name", "No Title")
        url = result.get("url", "No URL")

        # Check if the result belongs to one of the allowed domains
        domain = urlparse(url).netloc
        if not any(allowed_domain in domain for allowed_domain in allowed_domains):
            continue

        # Extract content from the URL
        try:
            webpage_content = extract_webpage_content(url)
            if webpage_content:  # Only include if content was successfully extracted
                formatted_results.append(f"**{title}**\n\n{webpage_content}\n\n_________________________________________")
        except Exception:
            # Skip this result if extraction fails
            continue

    # If no results match the allowed domains, return a message
    if not formatted_results:
        return "No results found from the specified domains."

    return "\n\n".join(formatted_results)
