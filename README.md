# AI Support Genius

The AI Support Genius is a Python-based tool that leverages the power of OpenAI's GPT-3.5 Turbo and Salesforce to assist with various support-related tasks, such as generating support cases, updating case details, and managing existing cases in Salesforce.

## Features

- **Support Case Generation**: Create realistic support cases with randomized content and categories to simulate real-world scenarios for testing purposes.

- **Support Case Update**: Automatically update the subjects, types, and priorities of existing support cases in Salesforce based on their content.

- **Support Case Deletion**: Quickly delete all support cases in Salesforce for clean slate testing.

## Prerequisites

Before using the AI Support Genius, ensure you have the following:

- Python 3.6 or higher installed on your system.

- A Salesforce account with the necessary API access and credentials.

- An OpenAI API key for using GPT-3.5 Turbo.

- Required Python libraries (dependencies) installed. You can install them using the `requirements.txt` file.

## Configuration

1. Create a `config.ini` file with the following structure and fill in your Salesforce and OpenAI credentials:

```ini
[Salesforce]
SF_USERNAME = your_salesforce_username
SF_PASSWORD = your_salesforce_password
SF_SECURITY_TOKEN = your_salesforce_security_token

[OpenAI]
OPENAI_API_KEY = your_openai_api_key
```

## Usage
1. Run the main.py script to start the AI Support Genius.
2. Follow the on-screen menu to choose from the available options, including generating new support cases, updating existing cases, and deleting cases.
3. Input the required information when prompted.

## Acknowledgments
- This project utilizes the power of OpenAI's GPT-3.5 Turbo for natural language processing tasks.
- It also relies on the Simple Salesforce library for interacting with Salesforce CRM.

## Disclaimer
This project is intended for testing and educational purposes. Use it responsibly and ensure that you have the necessary permissions and access rights to perform actions in your Salesforce environment.