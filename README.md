# Coding assistant: Codi!
**Codi** is a plugin for **JetBrains** IDE's that manages AI Agents to provide **IDE feature search** and **code insights** including error detection, linting and formatting.

## How it works
**Codi** is a plugin build in _Kotlin_. It parses user input and utilizes the **OpenAI** API to understand the requests and redirect them to the appropriate **Agent**. These Agents make use of tools which run in isolated, temporary **Docker containers** to process the user requests for the appropriate language.
Current support for Python and C/C++.

## The Agents
A total of four Agents are at the disposal of Codi:
- **Helper:** Leveraging of web-scraping agent for targeted, trustworthy knowledge bases such as the official JetBrains docs or StackOverflow.
- **Cleaner:** Pipeline of tools for debug tasks such as syntax error checking, memory leak and undefined behaviour detection with user-friendly output and insight (valgrind, fsanitize, ...)
- **Linter:** Code style checking and further error detection through language-specific linting/formatting tools such as clang-tidy, clang-format, pylint, etc
- **Optimizer:** Direct queries to the LLM about code optimization based on the given context (file).
