import os
import re
import time
from pyairtable import Api
import logging
from datetime import datetime
import openai

# Setup logging
logging.basicConfig(
    filename='error_log.txt',
    level=logging.ERROR,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Airtable setup
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = os.getenv('BASE_ID')

# Trigger table
TRIGGER_TABLE_NAME = 'tblAYeXyjc4rLwdwM'
CAMPAIGN_TABLE_NAME = 'tblCBGBYUu5WTHD0P'
PROGRAM_TABLE_NAME = 'tblBH1HxiY4FTNUkP'

# Initialize Airtable API
api = Api(AIRTABLE_API_KEY)
trigger_table = api.table(BASE_ID, TRIGGER_TABLE_NAME)
campaign_table = api.table(BASE_ID, CAMPAIGN_TABLE_NAME)
program_table = api.table(BASE_ID, PROGRAM_TABLE_NAME)

# OpenAI setup
api_key = os.getenv('OPENAI_API_KEY')
organization_id = os.getenv('OPENAI_ORGANIZATION_ID')
openai.api_key = api_key
openai.organization = organization_id

# Counter for API requests
openai_request_count = 0

# List of available types
CAMPAIGN_TYPES = [
    '📣 Announcement', '🤹 General - Pre', '🤹 General - During', '📣 Bounty', '📣 Workshop', '📣 Partnership', '📣 Speaker',
    '📣 Judge/mentor', '📆 Weekly Recap', '🤝 Partner Content', '🎤 Speaker Content', '📝 Summary', '🛫 Launch',
    '📺 Post-Launch', '🥁 Finale Promo', '📚 Weekly Workshops', '🥅 Submission Reminder', '🐦 Twitter Space',
    '🕵️‍♀️ Job ad', '🫴 Outreach', '📣 Community Partnership', '🎓 Society Partner Posts', '📸 On-site content'
]

# Helper function to convert ISO 8601 string to datetime
def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(date_string, '%Y-%m-%d')

# Step 1: Get all records from trigger table with the specified conditions
def get_triggered_records():
    records = trigger_table.all()
    filtered_records = []

    for record in records:
        fields = record['fields']
        if (fields.get('✏️ Channel') and 
            fields.get('Publisher') and 
            fields.get('Programmes(PP) Jamie') and 
            fields.get('Date for Automation') and 
            fields.get('Add Campaign/Initiative')):
            filtered_records.append(record)
    
    return filtered_records

# Step 2: Fetch Programme Dates and Programme Name, determine automation type (Pre, During, Post, Announce)
def fetch_programme_info_and_automation_type(programme_id, date_for_automation, publisher):
    record = program_table.get(programme_id)
    fields = record['fields']

    programme_name = fields.get('Name')  # Fetch the 'Name' field from the programme
    start_date = fields.get('✏️ Start Date (programme part)')
    end_date = fields.get('✏️ End Date (programme part)')
    announcement_date = fields.get('Announcement date')

    if start_date:
        start_date = parse_date(start_date)
    if end_date:
        end_date = parse_date(end_date)
    if announcement_date:
        announcement_date = parse_date(announcement_date)

    date_for_automation = parse_date(date_for_automation)

    # Determine the automation type based on dates
    automation_type = []
    
    if date_for_automation == announcement_date and publisher == 'Encode':
        automation_type.append('Announce')
    elif start_date and end_date:
        if date_for_automation < start_date:
            automation_type.append('Pre')
        elif start_date <= date_for_automation <= end_date:
            automation_type.append('During')
        elif date_for_automation > end_date:
            automation_type.append('Post')

    return programme_name, automation_type

# Step 3: Search campaign table based on 'Programme From Campaign Text' contains the Programme Name and 'Campaign - For Automations' contains conditions
def search_campaign_table(programme_name, automation_type):
    print(f"Searching for campaigns where 'Programme From Campaign Text' contains the Programme Name '{programme_name}' and 'Campaign - For Automations' contains {automation_type}")

    records = campaign_table.all()
    matched_records = []

    for record in records:
        fields = record['fields']
        programme_from_campaign_text = fields.get('Programme From Campaign Text', '')
        if programme_name in programme_from_campaign_text:
            campaign_for_automations = fields.get('Campaign - For Automations', [])
            if any(auto in campaign_for_automations for auto in automation_type):
                matched_records.append(record)

    if not matched_records:
        print(f"No records found where 'Programme From Campaign Text' contains '{programme_name}' and 'Campaign - For Automations' contains {automation_type}")
    
    return matched_records

# Step 4: Use OpenAI to determine the most relevant '✏️ Type' (aligned with your working code)
def find_most_relevant_type(records, programme_name, fields):
    global openai_request_count

    # Prepare the chat completion prompt
    prompt = f"Based on the following campaigns, which '✏️ Type' is the most relevant for the programme '{programme_name}'?\n"
    
    for record in records:
        campaign_type = record['fields'].get('✏️ Type')
        prompt += f"\nCampaign Type: {campaign_type}\n"

    # Add details from the deliverable
    deliverable_info = f"""
    ✏️ Channel: {fields.get('✏️ Channel')}
    Publisher: {fields.get('Publisher')}
    Notes: {fields.get('Notes', 'None')}
    Partner / Company: {fields.get('Partner / Company', 'None')}
    """
    prompt += f"\n\nDeliverable Information: {deliverable_info}\n\nIf you can't decide, pick the most general one."

    # Logging to see the exact prompt sent
    print(f"OpenAI Prompt: {prompt}")

    # OpenAI ChatCompletion request (following your provided structure)
    try:
        print("Sending request to OpenAI (ChatCompletion)...")
        
        client = openai.OpenAI(api_key=api_key)

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        openai_request_count += 1  # Increment the OpenAI API request count
        print("Waiting for OpenAI response...")

        # Check if response is valid
        if not completion.choices:
            print("Error: No choices returned from OpenAI.")
            return None

        # Extract the most relevant '✏️ Type' and match it to the predefined campaign types
        most_relevant_type = completion.choices[0].message.content.strip()

        # Match with available campaign types
        for campaign_type in CAMPAIGN_TYPES:
            if campaign_type in most_relevant_type:
                print(f"Matched '✏️ Type': {campaign_type}")
                return campaign_type

        print(f"No match found in campaign types. Defaulting to '🤹 General - During'")
        return '🤹 General - During'

    except Exception as e:
        logging.error(f"Error while calling OpenAI API: {str(e)}")
        print(f"Error occurred while calling OpenAI API: {str(e)}")
        return None

# Step 5: Perform a second search based on chosen '✏️ Type' and update the Initiative field
def search_by_type_and_update(programme_name, chosen_type, record_id):
    print(f"Searching again for campaigns where 'Programme From Campaign Text' contains '{programme_name}' and '✏️ Type' is '{chosen_type}'")

    records = campaign_table.all()
    for record in records:
        fields = record['fields']
        if (programme_name in fields.get('Programme From Campaign Text', '') and 
                fields.get('✏️ Type') == chosen_type):
            campaign_record_id = record['id']
            print(f"Found campaign with RecordID {campaign_record_id} and '✏️ Type' = {chosen_type}. Adding to Initiative.")
            update_initiative(record_id, campaign_record_id)
            return  # Exit after updating the first match

    print(f"No records found with 'Programme From Campaign Text' = '{programme_name}' and '✏️ Type' = '{chosen_type}'.")

# Step 6: Update the Initiative field in the Trigger Table
def update_initiative(record_id, campaign_record_id):
    print(f"Updating record {record_id} in the Initiative field with campaign RecordID {campaign_record_id}")
    trigger_table.update(record_id, {'Initiative': [campaign_record_id]})
    print(f"Record {record_id} successfully updated with Initiative RecordID {campaign_record_id}")

# Main logic
triggered_records = get_triggered_records()

# Output the number of records found in the trigger table
print(f"Total records found in trigger table meeting the criteria: {len(triggered_records)}")

for record in triggered_records:
    fields = record['fields']
    print(f"\nProcessing record: {fields.get('Name', 'Unnamed Record')}")

    programme_id = fields['Programmes(PP) Jamie'][0]  # Assuming it's a linked record list
    print(f"Programme ID: {programme_id}")

    date_for_automation = fields['Date for Automation']
    publisher = fields.get('Publisher')
    print(f"Date for Automation: {date_for_automation}")
    print(f"Publisher: {publisher}")

    # Fetch the programme name and dates and determine the automation type (Pre, During, Post, Announce)
    programme_name, automation_type = fetch_programme_info_and_automation_type(programme_id, date_for_automation, publisher)
    
    # Search campaign table based on the programme name and automation type
    campaigns = search_campaign_table(programme_name, automation_type)
    
    # Output the number of records found in the campaign table
    print(f"Total campaign records found for Programme Name '{programme_name}': {len(campaigns)}")

    # If only one campaign record is found, directly add the RecordID to Initiative
    if len(campaigns) == 1:
        campaign_record_id = campaigns[0]['id']
        print(f"Only one campaign record found. Adding RecordID: {campaign_record_id} to Initiative.")
        update_initiative(record['id'], campaign_record_id)
    elif len(campaigns) > 1:
        # Output details of each campaign record found
        for campaign in campaigns:
            campaign_fields = campaign['fields']
            print(f"Campaign Record: {campaign_fields.get('Name', 'Unnamed Campaign')}")
            print(f"Campaign Type: {campaign_fields.get('✏️ Type')}")
            print(f"Programme From Campaign Text: {campaign_fields.get('Programme From Campaign Text')}")

        # Find the most relevant '✏️ Type' using OpenAI
        most_relevant_type = find_most_relevant_type(campaigns, programme_name, fields)

        if most_relevant_type:
            # Search again with the chosen '✏️ Type' and update the initiative
            search_by_type_and_update(programme_name, most_relevant_type, record['id'])

# Output the total number of OpenAI API requests made
print(f"\nTotal OpenAI API requests made: {openai_request_count}")
