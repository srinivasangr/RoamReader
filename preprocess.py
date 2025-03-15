import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def extract_state_country(address):
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 3:
        last_part = parts[-1]
        if last_part.isdigit():  # Likely a ZIP code
            state = parts[-2]
            country = 'United States'
        else:
            country = last_part
            state = parts[-2] if len(parts) >= 4 else ''
    else:
        state = ''
        country = ''
    return state, country

def process_file(file_path, conn):
    with open(file_path, encoding='utf-8-sig') as file:
        data = json.load(file)
        cursor = conn.cursor()
        for obj in data['timelineObjects']:
            # Process Place Visits
            if 'placeVisit' in obj and 'location' in obj['placeVisit']:
                location = obj['placeVisit']['location']
                address = location.get('address', '')
                lat = location.get('latitudeE7', 0) / 10**7
                lon = location.get('longitudeE7', 0) / 10**7
                arrival = obj['placeVisit']['duration'].get('startTimestamp', '')
                departure = obj['placeVisit']['duration'].get('endTimestamp', '')
                visit_date = arrival.split('T')[0] if arrival else ''
                state, country = extract_state_country(address)
                
                duration_min = 0
                if arrival and departure:
                    try:
                        arrival_dt = datetime.strptime(arrival, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        arrival_dt = datetime.strptime(arrival, '%Y-%m-%dT%H:%M:%SZ')
                    
                    try:
                        departure_dt = datetime.strptime(departure, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        departure_dt = datetime.strptime(departure, '%Y-%m-%dT%H:%M:%SZ')
                    
                    duration_min = int((departure_dt - arrival_dt).total_seconds() / 60)

                cursor.execute("""
                    INSERT INTO place_visits (address, arrival, departure, duration_min, latitude, longitude, state, country, visit_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (address, arrival, departure, duration_min, lat, lon, state, country, visit_date))

            # Process Activity Segments
            if 'activitySegment' in obj:
                activity = obj['activitySegment']
                start_time = activity.get('duration', {}).get('startTimestamp', '')
                end_time = activity.get('duration', {}).get('endTimestamp', '')
                start_location = activity.get('startLocation', {})
                end_location = activity.get('endLocation', {})
                start_lat = start_location.get('latitudeE7', 0) / 10**7
                start_lon = start_location.get('longitudeE7', 0) / 10**7
                end_lat = end_location.get('latitudeE7', 0) / 10**7
                end_lon = end_location.get('longitudeE7', 0) / 10**7
                mode_of_travel = activity.get('activityType', '')
                distance = activity.get('distance', 0)  # Default to 0 if missing

                cursor.execute("""
                    INSERT INTO activity_segments (start_time, end_time, start_lat, start_lon, end_lat, end_lon, mode_of_travel, distance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (start_time, end_time, start_lat, start_lon, end_lat, end_lon, mode_of_travel, distance))

        conn.commit()

def setup_database():
    conn = sqlite3.connect('roamreader.db')
    cursor = conn.cursor()
    
    # Create tables if they don’t exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS place_visits (
        address TEXT, arrival TEXT, departure TEXT, duration_min INTEGER,
        latitude REAL, longitude REAL, state TEXT, country TEXT, visit_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_segments (
        start_time TEXT, end_time TEXT, start_lat REAL, start_lon REAL,
        end_lat REAL, end_lon REAL, mode_of_travel TEXT, distance INTEGER)''')
    
    # Check and add missing columns to place_visits
    cursor.execute("PRAGMA table_info(place_visits)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'state' not in columns:
        cursor.execute("ALTER TABLE place_visits ADD COLUMN state TEXT")
    if 'country' not in columns:
        cursor.execute("ALTER TABLE place_visits ADD COLUMN country TEXT")
    if 'visit_date' not in columns:
        cursor.execute("ALTER TABLE place_visits ADD COLUMN visit_date TEXT")
    
    conn.commit()
    return conn

def main():
    root_dir = Path(r"C:\Users\91944\Downloads\AWS\gmap_Rag\Takeout\Location History (Timeline)\Semantic Location History")
    if not os.path.exists(root_dir):
        print(f"Directory not found: {root_dir}")
        return
    
    conn = setup_database()
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".json"):
                process_file(os.path.join(subdir, file), conn)
    conn.close()
    print("Data successfully stored in roamreader.db")

if __name__ == "__main__":
    main()
    
    
    