import streamlit as st
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langchain.tools.retriever import create_retriever_tool
from typing import Annotated, Sequence, TypedDict
from helper import vectordb, chain_creator
from ingestion import load_data
from dotenv import load_dotenv
import os
load_dotenv()
api_key=os.getenv("google_api_key")
# === Setup Logging ===
logging.basicConfig(
    filename="logs/app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools.retriever import create_retriever_tool
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=api_key,
    max_tokens=500,
    temperature=0.1
)

def create_workflow(retriever):
    """Create LangGraph workflow for multi-agent system"""
    # Retriever Tool
    retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="document_retriever",
    description="Retrieve relevant documents from the database."
)


    # Define Agent State
    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    # Create Workflow Graph
    workflow = StateGraph(AgentState)

    # Define Nodes
    def query_agent(state: AgentState):
        """Query Agent: Retrieve relevant cricket information"""
        messages = state['messages']
        last_message = messages[-1]

        # Retrieve relevant documents
        retrieved_docs = retriever.invoke(last_message.content)

        return {
            "messages": [
                HumanMessage(content=f"Retrieved Documents: {retrieved_docs}")
            ]
        }

    def response_agent(state: AgentState):
        """Response Agent: Simplify information"""
        messages = state['messages']
        last_message = messages[-1]

        # Create summarization prompt - FIX: Remove input_variables parameter
        response_prompt = ChatPromptTemplate.from_template("""
    You are CricAI, a cutting-edge AI assistant specialized in cricket analysis and match insights for IPL 2025.

    You will be provided with the latest data from IPL 2025 — including match summaries, player stats, scores, and commentary.

    Your job is to:
    1. Understand and analyze the given context.
    2. Answer user questions with accurate, up-to-date information.
    3. If the context includes real-time or predictive data, use it to make logical, data-driven insights.
    4. Be concise, informative, and cricket-savvy in your tone.

    CONTEXT:
    {context}

    USER QUESTION:
    {user_query}

    CRICAI RESPONSE:
    """)  # The template method automatically identifies input variables

        # Response chain
        response_chain = (
            response_prompt
            | llm
            | StrOutputParser()
        )

        # Prepare context (first message is retrieved documents)
        context = messages[0].content
        query = messages[-1].content

        # Generate response
        response = response_chain.invoke({
            "context": context,
            "user_query": query
        })

        return {
            "messages": [HumanMessage(content=response)]
        }

    # Add nodes to workflow
    workflow.add_node("query_agent", query_agent)
    workflow.add_node("response_agent", response_agent)

    # Define edges
    workflow.add_edge(START, "query_agent")
    workflow.add_edge("query_agent", "response_agent")
    workflow.add_edge("response_agent", END)

    # Compile workflow
    app = workflow.compile()
    return app