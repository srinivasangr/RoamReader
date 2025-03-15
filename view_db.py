# import streamlit as st
# import sqlite3
# import pandas as pd

# def connect_db():
#     return sqlite3.connect('roamreader.db')

# def query_db(query):
#     conn = connect_db()
#     df = pd.read_sql_query(query, conn)
#     conn.close()
#     return df

# st.title("RoamReader Database Viewer")

# # Input for visit date
# visit_date = st.text_input("Enter visit date (YYYY-MM-DD)", "2023-05-27")

# if visit_date:
#     query = f"SELECT * FROM place_visits WHERE visit_date = '{visit_date}'"
#     df = query_db(query)
#     st.write(df)

import streamlit as st
import sqlite3
import pandas as pd

def connect_db():
    return sqlite3.connect('roamreader.db')

def query_db(query):
    conn = connect_db()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("RoamReader Database Viewer")

table = st.selectbox("Select table to view", ["place_visits", "activity_segments"])

if table:
    query = f"SELECT * FROM {table}"
    df = query_db(query)
    st.write(df)