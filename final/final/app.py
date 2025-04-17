import streamlit as st
import time
import threading
import pandas as pd
import os
import sys
from DataScrapper.DataScraperMatchLink import get_match_link, get_match_status, load_match_links
from DataScrapper.DataScrapperCommentary import get_commentary_js, close_driver
from DataScrapper.DataScrapperMain import load_data
from helper import vectordb
from workflow import create_workflow
from langchain_core.messages import HumanMessage

# Add proper error handling for imports
try:
    from langchain_core.messages import HumanMessage
except ImportError:
    st.error("Required packages not found. Please install all dependencies.")
    st.code("pip install langchain langchain-core langchain-google-genai streamlit selenium beautifulsoup4")
    st.stop()

# Set page configuration
st.set_page_config(
    page_title="CricAI - Real-time IPL Analysis",
    page_icon="🏏",
    layout="wide"
)

# Initialize session state
if 'commentary_list' not in st.session_state:
    st.session_state.commentary_list = []
if 'last_commentary_count' not in st.session_state:
    st.session_state.last_commentary_count = 0
if 'match_links' not in st.session_state:
    st.session_state.match_links = []
if 'match_statuses' not in st.session_state:
    st.session_state.match_statuses = {}
if 'selected_match_url' not in st.session_state:
    st.session_state.selected_match_url = ""
if 'selected_match_status' not in st.session_state:
    st.session_state.selected_match_status = ""
if 'workflow' not in st.session_state:
    st.session_state.workflow = None
if 'retriever' not in st.session_state:
    st.session_state.retriever = None
if 'data_loading_active' not in st.session_state:
    st.session_state.data_loading_active = False
if 'commentary_loading_active' not in st.session_state:
    st.session_state.commentary_loading_active = False

# Headers and description
st.title("CricAI: Real-time IPL 2025 Analysis")
st.markdown("""
This app provides real-time analysis of IPL 2025 matches using AI-powered insights. 
Select a match, view live commentary, and ask questions about the game!
""")

# Create necessary directories
os.makedirs("./chroma_db", exist_ok=True)
os.makedirs("./logs", exist_ok=True)

# Sidebar for controls
st.sidebar.header("Match Selection")

# Function to fetch match links
def refresh_match_links():
    with st.sidebar.status("Fetching latest matches..."):
        try:
            st.session_state.match_links = get_match_link()
            
            # Reset match statuses
            st.session_state.match_statuses = {}
            
            if st.session_state.match_links:
                st.session_state.match_links = st.session_state.match_links[:5]  # Limit to 5 matches
                return True
            else:
                # Try to load from saved file
                saved_links = load_match_links()
                if saved_links:
                    st.session_state.match_links = saved_links[:5]  # Limit to 5 matches
                    return True
                return False
        except Exception as e:
            st.sidebar.error(f"Error fetching match links: {e}")
            return False

# Button to refresh match links
if st.sidebar.button("Refresh Available Matches"):
    refresh_success = refresh_match_links()
    if refresh_success:
        st.sidebar.success(f"Found {len(st.session_state.match_links)} matches!")

# If no match links loaded yet, try to fetch them
if not st.session_state.match_links:
    refresh_match_links()

# Display match selection dropdown if links are available
match_options = []
if st.session_state.match_links:
    # Format match links for display
    match_options = [f"Match {link.split('/')[-1]}" for link in st.session_state.match_links[:5]]
    match_options.insert(0, "Select a match")
    
    selected_match = st.sidebar.selectbox(
        "Choose a match:",
        options=match_options,
        index=0,
        key="match_select"
    )
    
    # When a match is selected, update the URL and check status
    if selected_match != "Select a match":
        match_index = match_options.index(selected_match) - 1  # Adjust for "Select a match" at index 0
        new_url = st.session_state.match_links[match_index]
        
        # Only update if different from current selection
        if new_url != st.session_state.selected_match_url:
            st.session_state.selected_match_url = new_url
            
            # Check match status if not already known
            if new_url not in st.session_state.match_statuses:
                with st.sidebar.status("Checking match status..."):
                    st.session_state.match_statuses[new_url] = get_match_status(new_url)
            
            st.session_state.selected_match_status = st.session_state.match_statuses[new_url]
            status_indicator = "🔴 LIVE" if st.session_state.selected_match_status == "live" else "⚪ Completed"
            st.sidebar.success(f"Selected: Match {new_url.split('/')[-1]} ({status_indicator})")
else:
    st.sidebar.warning("No matches available. Use the refresh button.")

# Manual URL input option
st.sidebar.markdown("---")
st.sidebar.subheader("Manual Input")
manual_url = st.sidebar.text_input("Or enter match URL directly:", 
                                 placeholder="https://www.iplt20.com/match/2025/XXXX")

if st.sidebar.button("Use This URL"):
    st.session_state.selected_match_url = manual_url
    
    # Check match status
    with st.sidebar.status("Checking match status..."):
        st.session_state.match_statuses[manual_url] = get_match_status(manual_url)
    st.session_state.selected_match_status = st.session_state.match_statuses[manual_url]
    
    status_indicator = "🔴 LIVE" if st.session_state.selected_match_status == "live" else "⚪ Completed"
    st.sidebar.success(f"Using custom URL: {manual_url} ({status_indicator})")

# Innings selection
innings_number = st.sidebar.radio("Select Innings:", [1, 2])

# Main content area - divided into two columns
col1, col2 = st.columns([1, 1])

# Commentary section in first column
with col1:
    st.header("Match Commentary")
    commentary_container = st.container()
    
    # Function to update commentary in the background
    def update_commentary():
        while st.session_state.commentary_loading_active:
            if st.session_state.selected_match_url:
                try:
                    # Only actively poll if match is live
                    if st.session_state.selected_match_status == "live":
                        new_commentary = get_commentary_js(str(innings_number), st.session_state.selected_match_url)
                        if isinstance(new_commentary, list):
                            st.session_state.commentary_list = new_commentary
                        else:
                            st.session_state.commentary_list = [new_commentary]
                        time.sleep(10)  # Update every 10 seconds for live matches
                    else:
                        # For completed matches, fetch once and then stop
                        if not st.session_state.commentary_list:
                            new_commentary = get_commentary_js(str(innings_number), st.session_state.selected_match_url)
                            if isinstance(new_commentary, list):
                                st.session_state.commentary_list = new_commentary
                            else:
                                st.session_state.commentary_list = [new_commentary]
                        time.sleep(60)  # Check less frequently for completed matches
                except Exception as e:
                    print(f"Error fetching commentary: {e}")
                    time.sleep(30)  # Longer delay after error
    
    # Live match controls
    if st.session_state.selected_match_status == "live":
        st.info("🔴 LIVE MATCH - Commentary will update automatically")
        commentary_auto_refresh = st.checkbox("Auto-refresh commentary", value=True)
    else:
        st.info("⚪ COMPLETED MATCH - Showing full commentary")
        commentary_auto_refresh = st.checkbox("Auto-refresh commentary", value=False)
    
    # Handle auto-refresh thread
    if commentary_auto_refresh and not st.session_state.commentary_loading_active:
        st.session_state.commentary_loading_active = True
        commentary_thread = threading.Thread(target=update_commentary)
        commentary_thread.daemon = True
        commentary_thread.start()
    elif not commentary_auto_refresh:
        st.session_state.commentary_loading_active = False
    
    # Manual refresh button
    if st.button("Refresh Commentary Now"):
        if st.session_state.selected_match_url:
            try:
                with st.status("Fetching commentary..."):
                    new_commentary = get_commentary_js(str(innings_number), st.session_state.selected_match_url)
                    if isinstance(new_commentary, list):
                        st.session_state.commentary_list = new_commentary
                    else:
                        st.session_state.commentary_list = [new_commentary]
                st.success("Commentary refreshed!")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please select a match first")
    
    # Display commentary with the most recent at the top
    with commentary_container:
        with st.expander("📢 Live Commentary", expanded=True):
            commentary_box = st.empty()

            if st.session_state.commentary_list:
                # Format commentary nicely
                comment_text = ""
                for i, comment in enumerate(st.session_state.commentary_list):
                    comment_text += f"**Commentary {i+1}:** {comment}\n\n---\n\n"

                # Highlight new comments
                if len(st.session_state.commentary_list) > st.session_state.last_commentary_count:
                    new_count = len(st.session_state.commentary_list) - st.session_state.last_commentary_count
                    st.info(f"🆕 {new_count} new comments since last refresh")
                    st.session_state.last_commentary_count = len(st.session_state.commentary_list)

                # Display in the expander
                commentary_box.markdown(comment_text)

            else:
                commentary_box.info("No commentary available yet. Please select a match and refresh.")

# RAG Analysis section in second column
with col2:
    st.header("AI Match Analysis")
    
    # Function to load data in the background
    def update_vector_db():
        while st.session_state.data_loading_active:
            if st.session_state.selected_match_url:
                collection_name = f"ipl-{st.session_state.selected_match_url.split('/')[-1]}"
                
                try:
                    docs = load_data(st.session_state.selected_match_url)
                    st.session_state.retriever = vectordb(
                        docs_list=docs,
                        collection_name=collection_name,
                        persist_directory="./chroma_db"
                    )
                    
                    # Create workflow if not already done
                    if not st.session_state.workflow:
                        st.session_state.workflow = create_workflow(st.session_state.retriever)
                        
                    # Only actively update for live matches
                    if st.session_state.selected_match_status == "live":
                        time.sleep(20)  # Update every 20 seconds for live matches
                    else:
                        time.sleep(600)  # Update very infrequently for completed matches
                except Exception as e:
                    print(f"Error updating vector DB: {e}")
                    time.sleep(60)  # Wait longer after error
            else:
                time.sleep(5)  # Short sleep if no match selected
    
    # Toggle for data loading based on match status
    if st.session_state.selected_match_status == "live":
        data_auto_refresh = st.checkbox("Auto-refresh match data", value=True)
    else:
        data_auto_refresh = st.checkbox("Auto-refresh match data", value=False)
    
    if data_auto_refresh and not st.session_state.data_loading_active:
        st.session_state.data_loading_active = True
        data_thread = threading.Thread(target=update_vector_db)
        data_thread.daemon = True
        data_thread.start()
    elif not data_auto_refresh:
        st.session_state.data_loading_active = False
    
    # Manual data refresh button
    if st.button("Refresh Match Data Now"):
        if st.session_state.selected_match_url:
            with st.status("Loading match data..."):
                try:
                    collection_name = f"ipl-{st.session_state.selected_match_url.split('/')[-1]}"
                    docs = load_data(st.session_state.selected_match_url)
                    st.session_state.retriever = vectordb(
                        docs_list=docs,
                        collection_name=collection_name,
                        persist_directory="./chroma_db"
                    )
                    
                    # Create workflow
                    st.session_state.workflow = create_workflow(st.session_state.retriever)
                    st.success("Match data loaded successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please select a match first")
    
    # Query interface
    st.subheader("Ask about the match")
    user_query = st.text_input("Your question:", placeholder="Who's the top scorer so far?")
    
        # In app.py, replace the workflow invocation code in the "Get Analysis" button handler:
    if st.button("Get Analysis"):
        if not st.session_state.workflow or not st.session_state.retriever:
            st.warning("Please refresh match data first before asking questions")
        elif user_query:
            try:
                with st.status("Analyzing..."):
                    # Use the workflow to process the query
                    # Based on the error, the workflow expects messages
                    result = st.session_state.workflow.invoke({
                        "messages": [HumanMessage(content=user_query)]
                    })
                    
                    # Extract the answer from the last message
                    answer = result["messages"][-1].content
                
                # Display the answer
                st.info("CricAI Analysis")
                st.markdown(answer)
            except Exception as e:
                st.error(f"Error generating analysis: {e}")
        else:
            st.warning("Please enter a question")
# Display active match info
if st.session_state.selected_match_url:
    st.markdown("---")
    match_id = st.session_state.selected_match_url.split('/')[-1]
    status_indicator = "🔴 LIVE" if st.session_state.selected_match_status == "live" else "⚪ Completed"
    st.subheader(f"Active Match: Match {match_id} ({status_indicator})")
    st.markdown(f"URL: {st.session_state.selected_match_url}")
    st.markdown(f"Viewing Commentary for Innings {innings_number}")
else:
    st.markdown("---")
    st.info("Select a match to begin analysis")

# Footer with clean-up
st.markdown("---")
st.caption("CricAI - Real-time IPL 2025 Analysis powered by RAG | © 2025")

# Clean up when the app is closed
def cleanup():
    close_driver()

# Register the cleanup function
import atexit
atexit.register(cleanup)