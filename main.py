"""
Main implementation of the multi-agent copilot.
"""

# General imports
from typing import Annotated, Literal, TypedDict, Sequence, Callable
import asyncio
import os
from langchain_core import messages
from pydantic import BaseModel, Field
import operator
import functools
from dotenv import load_dotenv
import requests

# Langchain
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

# Langgraph
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

# Tools
from tools import bing_search, run_python_docker, clean_c_docker, lint_c_docker

chat_history = []


# Defining State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: Literal["Checker", "Optimizer", "Sanitizer", "Helper", "END"]
    sender: Literal["Checker", "Optimizer", "Sanitizer", "Helper", "END"]


# Creating the agent -> Basically a model that can call tools and gives output in a specific manner
def create_agent(tools: list, system_prompt: str):

    model = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.15, max_tokens=4000)

    if len(tools) > 0:
        model = model.bind_tools(tools, tool_choice="auto")

    prompt = ChatPromptTemplate.from_messages([("system", "{system_prompt}"),
                                               MessagesPlaceholder(variable_name="messages")
                                              ]).partial(system_prompt=system_prompt)

    # Agent is a chain of the prompt and the model
    agent = (prompt | model)

    return agent


# Defining the agent node -> Basically to define a node you have to have a function with a state parameter and
async def agent_node(state, agent, name):

    result = await agent.ainvoke(state)
    #print(f"\n\n {result.content} \n\n")

    if result.tool_calls:
        print(result)
        pass
    else:
        result = AIMessage(content=result.content, name=name)

    return {"messages": [result], "sender": name}


async def main():

    # Load environment variables
    load_dotenv()

    # Define the model for the supervisor
    model = ChatOpenAI(model="gpt-4o",
                       api_key=os.getenv("OPENAI_API_KEY"),
                       max_retries=1,
                       max_tokens=5000,
                       temperature=0.25)

    # Define worker nodes
    workers = ["Linter", "Optimizer", "Sanitizer", "Helper"]

    supervisor_system_prompt = (
        "You are a supervisor in the context of a multi-agent coding copilot for Jetbrains IDEs."
        "You are responsible for overseeing the work of the following agents: {workers}"
        "Given the following user request, respond with the worker to act next. Each worker will perform a task and respond with their results and status. When finished, respond with FINISH."
    )

    class routeResponse(BaseModel):
        next: Literal["Linter", "Optimizer", "Sanitizer", "Helper"]

    supervisorPrompt = ChatPromptTemplate.from_messages([
        ("system", supervisor_system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", """ Given the conversation above, who should act next? Keep the following in mind: /
                The sanitizer is supposed to find errors in the code. It will compile the code and run code sanitizers such as Valgrind.
                The optimizer is a general solution that should be used when the user wants to generate code, optimize an existing piece of code or wants an explanation for a piece of code.
                The linter is going to run linters in the background to find style errors. 
                The helper is supposed to answer questions about Jetbrains or general questions the user might ask that are unrelated to code.
                Select one of: {workers}
                """)
    ]).partial(workers=str(workers))

    # Supervisor is a node that routes the conversation to the next worker
    async def supervisor_agent(state):
        supervisor_chain = supervisorPrompt | model.with_structured_output(routeResponse)
        response = await supervisor_chain.ainvoke(state)
        return response

    ### Creating Agents -> Using functools.partial to set agent and name parameters ###
    linter_prompt = """You are a linter agent. You are responsible for running linters in the background to find style errors. Follow the steps below: 
    1 - You will run the linter tool based on the programming language of the code. This is a dict based on language and tool name: {"c" : "lint_c_docker"}.
    2 - You will provide the user with a simplified version of the output of the linter tool.
    """
    linter_agent = functools.partial(agent_node, agent=create_agent([lint_c_docker], linter_prompt), name="Linter")

    optimizer_prompt = "You are an optimizer agent. You are a general solution that should be used when the user wants to generate code, optimize an existing piece of code or wants an explanation for a piece of code."
    optimizer_agent = functools.partial(agent_node, agent=create_agent([], optimizer_prompt), name="Optimizer")

    sanitizer_prompt = """You are a sanitizer agent. You are responsible for finding errors in the code. Do the following steps:
    1 - You will compile the code and run the code based on which programming language it is. This is a dict based on language and tool name: {"c" : "clean_c_docker", "python" : "run_python_docker"}.
    2 - Make sure you provide to the user a simplified version of the output of the sanitizer tool."""
    sanitizer_agent = functools.partial(agent_node,
                                        agent=create_agent([clean_c_docker, run_python_docker], sanitizer_prompt),
                                        name="Sanitizer")

    helper_prompt = "You are a helper agent. You are responsible for answering questions about Jetbrains or general questions the user might ask that are unrelated to code. If you are asked a questions related to Jetbrains, always use the bing_search tool to find the answer."
    helper_agent = functools.partial(agent_node, agent=create_agent([bing_search], helper_prompt), name="Helper")

    ### Define the StateGraph ###
    graph = StateGraph(AgentState)
    graph.add_node("Supervisor", supervisor_agent)
    graph.add_node("Linter", linter_agent)
    graph.add_node("Optimizer", optimizer_agent)
    graph.add_node("Sanitizer", sanitizer_agent)
    graph.add_node("Helper", helper_agent)

    # Define the function that determines which agent to route to
    def choose_agent(state) -> Literal["Linter", "Optimizer", "Sanitizer", "Helper"]:
        return state["next"]

    # Maps each node name to the corresponding agent
    conditional_map = {k: k for k in workers}
    graph.add_conditional_edges("Supervisor", choose_agent, conditional_map)

    # Setup Tools
    sanitizer_tools = ToolNode([clean_c_docker, run_python_docker])
    optimizer_tools = ToolNode([])
    linter_tools = ToolNode([lint_c_docker])
    helper_tools = ToolNode([bing_search])

    graph.add_node("SanitizerTools", sanitizer_tools)
    graph.add_node("OptimizerTools", optimizer_tools)
    graph.add_node("LinterTools", linter_tools)
    graph.add_node("HelperTools", helper_tools)

    def router_tools(state):
        messages = state['messages']
        last_message = messages[-1]

        if last_message.tool_calls:
            return state["next"] + "Tools"

        return "END"

    graph.add_conditional_edges("Sanitizer", router_tools, {"SanitizerTools": "SanitizerTools", "END": END})
    graph.add_conditional_edges("Optimizer", router_tools, {"OptimizerTools": "OptimizerTools", "END": END})
    graph.add_conditional_edges("Linter", router_tools, {"LinterTools": "LinterTools", "END": END})
    graph.add_conditional_edges("Helper", router_tools, {"HelperTools": "HelperTools", "END": END})

    graph.add_edge("SanitizerTools", "Sanitizer")
    graph.add_edge("OptimizerTools", "Optimizer")
    graph.add_edge("LinterTools", "Linter")
    graph.add_edge("HelperTools", "Helper")

    graph.add_edge(START, "Supervisor")

    workflow = graph.compile()

    test_input = """
please lint the following code:

#include<stdio.h> // Missing space between includes

void unused_function() { // Unused function
    printf("This function is not used!\n");
}

int main(){

    int x=10,y=20; // Missing spaces around operators
    if(x>y) // Missing spaces around operator
    {
        printf("X is greater\n");
    }else{
        printf( "Y is greater or equal\n"); // Inconsistent spacing
    }

    for(int i=0;i<5;i++){ printf("%d\n",i); } // Single-line loop (not recommended)

    return 0;
}
    """
    response = await workflow.ainvoke({"messages": [HumanMessage(content=repr(test_input))]})
    print(response["messages"][-1].content)

    # message_history = []
    # while True:
    #     input_text = input("Enter your message: ")
    #     message_history.append(HumanMessage(content=input_text))
    #     response = await workflow.ainvoke({"messages": message_history})
    #     message_history = response["messages"]
    #     response_text = response["messages"][-1].content
    #     print(f"Response: {response_text}")


# Run main with asyncio
if __name__ == "__main__":
    asyncio.run(main())
