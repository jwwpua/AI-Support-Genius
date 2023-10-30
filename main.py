# Import necessary libraries
import openai
from simple_salesforce import Salesforce
import random
from random import choice
from datetime import datetime, timedelta
import re
from concurrent.futures import ThreadPoolExecutor
import time
from time import sleep
from requests.exceptions import ConnectionError, Timeout
import threading
import configparser

# Read configuration from 'config.ini' file
config = configparser.ConfigParser()
config.read('config.ini')

# Get Salesforce and OpenAI credentials from the configuration file
SF_USERNAME = config['Salesforce']['SF_USERNAME']
SF_PASSWORD = config['Salesforce']['SF_PASSWORD']
SF_SECURITY_TOKEN = config['Salesforce']['SF_SECURITY_TOKEN']
OPENAI_API_KEY = config['OpenAI']['OPENAI_API_KEY']

# Authenticate with Salesforce
sf = Salesforce(username=SF_USERNAME, password=SF_PASSWORD, security_token=SF_SECURITY_TOKEN)

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# List of available support case types
available_types = ["Login Help", "Payment Question", "Bank Deposit", "Technical", "Invoice Balance", "Reconciliation", "Feature Request", "Bug", "SSO", "Bill Image / PDF", "File Import", "Data Request", "Training", "Web Service", "Documentation", "Other"]

# Function to make an asynchronous API call to OpenAI
def api_caller(result, messages, max_tokens, temperature, timeout=700):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        result.append(response['choices'][0]['message']['content'].strip())
    except (OpenAIAPIError, Timeout) as e:
        result.append(e)

# Function to call OpenAI with retries
def call_openai(messages, max_tokens=50, temperature=0.8, retries=3, delay=5, timeout=5):
    for i in range(retries):
        result = []
        api_thread = threading.Thread(target=api_caller, args=(result, messages, max_tokens, temperature))
        api_thread.daemon = True
        api_thread.start()
        api_thread.join(timeout=timeout)

        if result:
            if isinstance(result[0], Exception):
                print(f"Attempt {i+1} failed due to {result[0]}. Retrying in {delay}s.")
                sleep(delay)
                continue
            else:
                return result[0]
    else:
        print("Max retries reached. Exiting.")
        return None

# Function to strip specified characters from a string
def strip_chars(subject, chars=['"', '[', ']', '.']):
    return subject[1:-1] if subject.startswith(tuple(chars)) and subject.endswith(tuple(chars)) else subject

# Function to generate a single dummy support case
def generate_single_dummy_case(case_num, available_types, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            # Generate the content of the support case
            case_content = call_openai([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Written like a human submitting a support ticket, please generate the body of a {choice(['support ticket'])} from a {choice(['client (biller)', 'end user (payer)'])} categorized as {choice(available_types)}, but do not include a subject."}
            ], max_tokens=250, timeout=10)

            # Generate a vague and unhelpful subject for the case
            case_subject = strip_chars(call_openai([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Generate a very vague and unhelpful subject based on the following case content, even if it doesn't describe it well: {case_content}"}
            ]))
            case_subject = case_subject[case_subject.rfind(': ')+2:] if ': ' in case_subject else case_subject
            print(f"Thread {case_num} created case with subject: {case_subject}")

            # Create the support case in Salesforce
            sf.Case.create({'Subject': case_subject, 'Description': case_content})
            return

        except Exception as e:
            print(f"Thread {case_num} encountered an error: {str(e)}")
            if attempt < max_retries:
                print(f"Retrying... ({attempt}/{max_retries})")
                time.sleep(2**attempt)
            else:
                return f"Thread {case_num} failed to create a case after {max_retries} attempts."

# Function to generate multiple dummy support cases
def generate_dummy_cases(num_cases, available_types):
    print(f"\nGenerating {num_cases} new cases...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(generate_single_dummy_case, range(num_cases), [available_types]*num_cases))
    for result in [r for r in results if r is not None]:
        print(result)
    print(f"\n{num_cases} new cases generated successfully.")

# Function to delete all support cases in Salesforce
def delete_all_support_cases(retries=3, delay=5):
    print("\nDeleting all support cases...")
    for i in range(retries):
        try:
            cases = sf.query_all("SELECT Id FROM Case")
            case_ids = [case['Id'] for case in cases['records']]
            break
        except (ConnectionError, Timeout):
            print(f"Attempt {i+1} failed. Retrying in {delay}s.")
            sleep(delay)
            continue
    else:
        print("Max retries reached. Exiting.")
        return

    for case_id in case_ids:
        try:
            sf.Case.delete(case_id)
            print(f"Deleted case with ID: {case_id}")
        except (ConnectionError, Timeout):
            print(f"Failed to delete case with ID: {case_id}")

    print("\nAll support cases have been deleted.")

# Function to generate a subject for a support case
def generate_subject(case_content):
    # Generate the subject using the call_openai function
    subject = call_openai([
        {"role": "system", "content": "You are a helpful expert support case analyst assistant."},
        {"role": "user", "content": f"Please return ONLY a short but highly detailed subject for the following support case: {case_content}"}
    ], max_tokens=50, temperature=0.4)
    
    # Strip surrounding quotes, surrounding square brackets, trailing periods
    subject = re.sub(r'^["\'](.*)["\']$', r'\1', subject)    
    subject = re.sub(r'^\[(.*)\]$', r'\1', subject)
    subject = re.sub(r'\.$', '', subject) 
    subject = subject[subject.rfind(': ')+2:] if ': ' in subject else subject

    return subject

# Function to generate a category for a support case
def generate_category(case_content):
    generated_category = call_openai([
        {"role": "system", "content": "You are a helpful expert support case analyst assistant."},
        {"role": "user", "content": f"Please return ONLY the most appropriate category for the following support case. Choose one of these: {', '.join(available_types)}\n---\n{case_content}"}
    ], max_tokens=50, temperature=0.5)

    return generated_category if generated_category in available_types else "Other"

# Function to generate a priority for a support case
def generate_priority(case_content):
    priority = strip_chars(call_openai([
        {"role": "system", "content": "You are a helpful expert support case analyst assistant."},
        {"role": "user", "content": f"Please respond with ONLY the appropriate priority level (Low, Medium, High) for the following support case: {case_content}"}
    ], max_tokens=10, temperature=0.4))

    return priority

# Function to update subjects, types, and priorities for existing support cases
def update_case_subjects_and_types(retries=3, delay=5):
    print("\nUpdating subjects, types, and priority for existing cases...\n")
    
    # Query Cases with Retries
    for i in range(retries):
        try:
            cases = sf.query("SELECT Id, Description, Subject FROM Case")['records']
            break
        except (ConnectionError, Timeout) as e:
            print(f"Query attempt {i+1} failed due to {e}. Retrying in {delay}s.")
            sleep(delay)
            continue
    else:
        print("Max query retries reached. Exiting.")
        return
    
    # Iterate and Update Cases
    for case in cases:
        case_id = case['Id']
        case_content = case['Description']
        old_subject = case['Subject']
        
        for i in range(retries):
            try:
                new_subject = generate_subject(case_content)
                new_category = generate_category(case_content)
                new_priority = generate_priority(case_content)
                
                update_data = {'Subject': new_subject[:255], 'Type': new_category, 'Priority': new_priority}
                sf.Case.update(case_id, update_data)
                
                print(f"[Case # {case_id}]\n Old subject: {old_subject}\n New subject: {new_subject[:255]}\n    New Type: {new_category}\nNew Priority: {new_priority}\n")
                break
            except (ConnectionError, Timeout) as e:
                print(f"Update attempt {i+1} for case {case_id} failed due to {e}. Retrying in {delay}s.")
                sleep(delay)
                continue
        else:
            print(f"Max update retries reached for case {case_id}. Skipping.")
    
    print("Subjects, types, and priorities updated successfully.")

# Main function to interact with the user and perform actions
def main():
    while True:
        print("\n[Menu]")
        print("1. Generate new cases")
        print("2. Update subjects and types for existing cases")
        print("3. Delete all cases")
        print("Q. Quit")
        choice = input("\nEnter your choice (1/2/3/Q): ")

        if choice == '1':
            num_cases = int(input("Enter the number of cases to generate: "))
            generate_dummy_cases(num_cases, available_types)
        elif choice == '2':
            update_case_subjects_and_types()
        elif choice == '3':
            delete_all_support_cases()
        elif choice.lower() == 'q':
            break
        else:
            print("Invalid choice. Please try again.")
            
if __name__ == "__main__":
    main()
