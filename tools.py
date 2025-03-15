import sqlite3
import folium
from streamlit_folium import folium_static
import streamlit as st
from openai import OpenAI

def connect_db():
    return sqlite3.connect('roamreader.db')

# Tool 1: Text-to-SQL
def text_to_sql_tool(query, api_key):
    conn = connect_db()
    client = OpenAI(api_key=api_key)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(place_visits)")
    place_cols = [col[1] for col in cursor.fetchall()]
    cursor.execute("PRAGMA table_info(activity_segments)")
    activity_cols = [col[1] for col in cursor.fetchall()]
    
    prompt = f"""
    Generate an SQLite SQL query for:
    - Tables: 
      - place_visits: {', '.join(place_cols)}
      - activity_segments: {', '.join(activity_cols)}
    - Date format: 'YYYY-MM-DD' (visit_date) or 'YYYY-MM-DDTHH:MM:SS[.SSS]Z' (timestamps).
    - Date queries (e.g., 'places on May 27 2023'): use place_visits.visit_date.
    - Duration (e.g., 'how long in California'): use place_visits.duration_min with state/country/address.
    - Place lists by area (e.g., 'places in California'): search place_visits.address/state/country LIMIT 5.
    - Countries/states visited: use place_visits.country/state with DISTINCT.
    - Travel mode/distance (e.g., 'how far did I travel'): use activity_segments.mode_of_travel/distance.
    - If user uses state short forms (e.g., 'CA' for California): map to place_visits.state.
    Query: '{query}'
    Return only the SQL query.
    """
    
    try:
        # Generate SQL
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        sql = response.choices[0].message.content.strip()
        
        # Execute SQL and limit to top 5
        cursor.execute(sql + " LIMIT 5")  # Ensure top 5 records
        results = cursor.fetchall()
        
        # Generate ChatGPT description based on results
        result_str = "\n".join([str(row) for row in results])
        desc_prompt = f"""
        Based on these visited places:\n{result_str}\n
        Provide a short description of the user's travel activity.
        """
        desc_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": desc_prompt}],
            max_tokens=150
        )
        description = desc_response.choices[0].message.content.strip()
        
        conn.close()
        return {
            "sql": sql,
            "results": results[:5],  # Top 5 records
            "description": description
        }
    except Exception as e:
        conn.close()
        return f"Error: {e}"

# Tool 2: Map Creation
def map_creation_tool(query, api_key):
    conn = connect_db()
    client = OpenAI(api_key=api_key)
    
    # Extract location (e.g., "California") from query
    prompt = f"Extract the location from this query: '{query}'"
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    location = response.choices[0].message.content.strip()
    
    # Filter places by state (simplified approach using state column)
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude, address FROM place_visits WHERE state = ? OR address LIKE ?",
                   (location, f"%{location}%"))
    locations = cursor.fetchall()
    conn.close()
    
    if not locations:
        return "No places found in that location."
    
    # Create Folium map
    m = folium.Map()
    for lat, lon, _ in locations:
        folium.Marker([lat, lon]).add_to(m)
    min_lat, max_lat = min(l[0] for l in locations), max(l[0] for l in locations)
    min_lon, max_lon = min(l[1] for l in locations), max(l[1] for l in locations)
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
    
    # Get spot names
    coords_str = "\n".join([f"Lat: {lat}, Lon: {lon}" for lat, lon, _ in locations])
    prompt = f"Given these coordinates:\n{coords_str}\nProvide spot names."
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    spot_names = response.choices[0].message.content.strip().split('\n')
    
    # Store in session state for Streamlit display
    st.session_state['map'] = m
    st.session_state['spot_names'] = spot_names
    return f"Map generated for {location} with {len(locations)} places."

# Tool 3: Analytical
def analytical_tool(query, api_key):
    conn = connect_db()
    cursor = conn.cursor()
    
    if "countries" in query.lower():
        cursor.execute("SELECT DISTINCT country FROM place_visits WHERE country != ''")
        results = cursor.fetchall()
        conn.close()
        return "Countries visited: " + ", ".join([r[0] for r in results]) if results else "No countries found."
    elif "states" in query.lower():
        cursor.execute("SELECT DISTINCT state FROM place_visits WHERE state != ''")
        results = cursor.fetchall()
        conn.close()
        return "States visited: " + ", ".join([r[0] for r in results]) if results else "No states found."
    else:
        conn.close()
        return "Unsupported analytical query."