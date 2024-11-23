"""
This file contains the tools that will be used in the LLM.
"""

# General imports
import requests
import docker
import uuid
import tempfile
import docker.utils

from utils import trimMd

# Langchain
from langchain_core.tools import tool


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


# Python error check
@tool
def runPythonDocker(code: str) -> dict:
    """
    Runs Python code insider a docker container and returns the output or errors.

    Args:
        code (str) : Python code to execute.
    
    Returns:
        dict: Contains "success" (bool), "output" (str) and "error" (str).
    """

    # Remove the markdown delimiters from the given code string
    code = trimMd(code)

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
        logs = container.logs().decode("utf-8")

        # Clean up container
        container.remove()

        if exit_status == 0:
            return {"success": True, "output": logs, "error": None}
        else:
            return {"success": False, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


# C sanitizer
@tool
def cleanCDocker(code: str, params: list) -> dict:
    """
    Compiles C code in docker container and runs valgrind leak sanitization to report potential leaks.

    Args:
        code (str): The C source code to compile and sanitize using leak sanitizer and valgrind.
        params (list): A list of strings representing the parameters that are given to the c code to run.

    Returns:
        dict: Contains the success flag, sanitize (valgrind+fsaniitze) output, and any errors.
    """

    # Remove the markdown delimiters from the given code string
    code = trimMd(code)
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
                f"valgrind --leak-check=full --track-origins=yes ./{executable_filename_valgrind} {' '.join(params)}'")

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
            logs = container.logs().decode("utf-8")
            print(logs)
            print(exit_status)

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
def lintCDocker(code: str) -> dict:
    """
    Lints C code in docker container with clang-tidy to enforce code style.

    Args:
        code (str): The C source code to lint.

    Returns:
        dict: Contains the success flag, linting output, and any errors.
    """

    # Remove the markdown delimiters from the given code string
    code = trimMd(code)

    try:
        client = docker.from_env()

        source_filename = f"/tmp/{uuid.uuid4().hex}.c"

        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(code)
            temp_file.close()

            # Command to lint the code using clang-tidy
            command = f"sh -c 'clang-tidy {source_filename} --'"

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
            logs = container.logs().decode('utf-8')

            # Cleanup container
            container.remove()

            if exit_status == 0:
                return {"success": True, "output": logs, "error": None}
            else:
                return {"success": True, "output": None, "error": logs}

    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}
