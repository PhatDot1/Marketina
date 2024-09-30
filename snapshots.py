import os
import requests
from datetime import datetime

# Airtable setup
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = 'app5tluywVKZ9oKHM'
TABLE_NAME = 'tblVbK3pzyBlaWwBt'
VIEW_ID = 'viwwmV3g7lGoDWyqn'  # The specific view to act on
AIRTABLE_URL = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?view={VIEW_ID}'
HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json'
}

# Get current day of the week
today = datetime.now().strftime('%A')  # E.g., 'Monday', 'Tuesday'

# Map days of the week to Airtable fields
day_to_field = {
    'Monday': 'temp-test',
    'Tuesday': 'temp-test1',
    'Wednesday': '📸 WED',
    'Thursday': '📸 THU',
    'Friday': '📸 FRI',
    'Saturday': '📸 SAT',
    'Sunday': '📸 SUN'
}

# Function to get all records in the specified view
def get_records():
    response = requests.get(AIRTABLE_URL, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get('records', [])
    else:
        print(f"Failed to fetch records. Response: {response.content}")
        return []

# Function to update the respective day's field for each record
def update_day_field(day_field, reg_app_value, record_id):
    # Handle cases where reg_app_value is a list
    if isinstance(reg_app_value, list):
        reg_app_value = reg_app_value[0] if reg_app_value else None  # Use the first item if available
    
    if reg_app_value is not None:
        try:
            reg_app_value = int(reg_app_value)  # Ensure the value is an integer (assuming it's whole numbers)
        except ValueError:
            print(f"Invalid value for # Reg/App: {reg_app_value}")
            return

        data = {
            "records": [
                {
                    "id": record_id,  # The specific record ID to update
                    "fields": {
                        day_field: reg_app_value
                    }
                }
            ]
        }

        response = requests.patch(AIRTABLE_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            print(f"Updated {day_field} with {reg_app_value} for record {record_id}")
        else:
            print(f"Failed to update {day_field} for record {record_id}. Response: {response.content}")
    else:
        print(f"No valid # Reg/App value to update for record {record_id}")

def main():
    records = get_records()
    if records:
        day_field = day_to_field.get(today)
        if day_field:
            for record in records:
                reg_app_value = record['fields'].get('# Reg/App')
                record_id = record['id']
                if reg_app_value is not None:
                    update_day_field(day_field, reg_app_value, record_id)
                else:
                    print(f"No # Reg/App value for record {record_id}")
        else:
            print(f"Today is {today}, no matching field to update.")
    else:
        print("No records found in the specified view.")

if __name__ == '__main__':
    main()
