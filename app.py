import streamlit as st
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from tools import text_to_sql_tool, map_creation_tool, analytical_tool
from streamlit_folium import folium_static
import subprocess
import os

# Sidebar setup
st.sidebar.title("RoamReader Setup")
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
user_name = st.sidebar.text_input("Enter Your Name")
file_path = st.sidebar.text_input("Enter Semantic Location History Folder Path", 
                                  value=r"C:\Users\91944\Downloads\AWS\gmap_Rag\Takeout\Location History (Timeline)\Semantic Location History")

if st.sidebar.button("Preprocess"):
    if not api_key or not user_name or not os.path.exists(file_path):
        st.sidebar.error("Please fill all fields with valid inputs.")
    else:
        with st.spinner("Preprocessing..."):
            try:
                with open("preprocess.py", "r") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.strip().startswith("root_dir = Path("):
                        lines[i] = f'    root_dir = Path(r"{file_path}")\n'
                with open("preprocess.py", "w") as f:
                    f.writelines(lines)
                result = subprocess.run(["python", "preprocess.py"], capture_output=True, text=True)
                if result.returncode == 0:
                    st.sidebar.success(f"Database updated for {user_name}!")
                else:
                    st.sidebar.error(f"Error: {result.stderr}")
            except Exception as e:
                st.sidebar.error(f"Failed: {e}")

# Main UI
st.title("# RoamReader")
st.write("Analytics Chatbot for your Travel History!")

if api_key and user_name and os.path.exists(file_path):
    tools = [
        Tool(name="TextToSQL", func=lambda q: text_to_sql_tool(q, api_key),
             description="Use for date-based queries (e.g., 'places on May 27 2023'), duration, place lists by area (e.g., 'places in California'), or country/state summaries. Use activity_segments for travel mode/distance."),
        Tool(name="MapCreation", func=lambda q: map_creation_tool(q, api_key),
             description="Use for location-based queries with maps (e.g., 'map of places in California')."),
        Tool(name="Analytical", func=lambda q: analytical_tool(q, api_key),
             description="Use for summary queries (e.g., 'countries visited').")
    ]
    
    llm = OpenAI(api_key=api_key, temperature=0)
    memory = ConversationBufferMemory(memory_key="chat_history", max_token_limit=500)
    agent = initialize_agent(
        tools, llm, agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory, verbose=True, max_iterations=3
    )
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    query = st.chat_input(f"Ask me anything about your travels, {user_name}!")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)
        
        with st.chat_message("assistant"):
            try:
                response = agent.run(query)
                if isinstance(response, dict):  # From TextToSQL
                    st.write(f"**SQL Query Used:** `{response['sql']}`")
                    st.write("**Top 5 Places:**")
                    for i, row in enumerate(response['results'], 1):
                        st.write(f"{i}. {row[0]}")  # Assuming address is first column
                    st.write("**Description:**", response['description'])
                else:  # From other tools
                    st.write(response)
                    if 'map' in st.session_state:
                        folium_static(st.session_state['map'])
                        st.write("Spot Names:", ", ".join(st.session_state['spot_names']))
                        del st.session_state['map']
                        del st.session_state['spot_names']
            except Exception as e:
                st.write(f"Error: {e}")
        st.session_state.messages.append({"role": "assistant", "content": str(response)})
else:
    st.write("Please complete the setup in the sidebar!")