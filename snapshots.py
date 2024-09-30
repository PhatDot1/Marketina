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
    'Monday': '📸 MON',
    'Tuesday': '📸 TUE',
    'Wednesday': '📸 WED',
    'Thursday': '📸 THU',
    'Friday': '📸 FRI',
    'Saturday': '📸 SAT',
    'Sunday': '📸 SUN'
}

# Function to get the current # Reg/App value from the specific view
def get_reg_app_value():
    response = requests.get(AIRTABLE_URL, headers=HEADERS)
    if response.status_code == 200:
        records = response.json().get('records', [])
        if records:
            return records[0]['fields'].get('# Reg/App')
    return None

# Function to update the respective day's field
def update_day_field(day_field, reg_app_value, record_id):
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

def main():
    response = requests.get(AIRTABLE_URL, headers=HEADERS)
    if response.status_code == 200:
        records = response.json().get('records', [])
        if records:
            reg_app_value = records[0]['fields'].get('# Reg/App')
            record_id = records[0]['id']
            if reg_app_value is not None:
                day_field = day_to_field.get(today)
                if day_field:
                    update_day_field(day_field, reg_app_value, record_id)
                else:
                    print(f"Today is {today}, no matching field to update.")
            else:
                print("Could not retrieve # Reg/App value.")
        else:
            print("No records found in the specified view.")
    else:
        print(f"Failed to fetch records. Response: {response.content}")

if __name__ == '__main__':
    main()
