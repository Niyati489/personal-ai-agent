# Personal AI Agent

A Python-based personal AI assistant powered by Google's Gemini API.

## Features

- **AI Chat:** Answers questions using the Gemini API.
- **Short-term Memory:** Maintains conversation context during a session.
- **Long-term Memory:** Saves selected information in a local JSON file.
- **Tool Calling:** Uses Python functions to perform tasks.
- **Calculator:** Performs basic mathematical calculations.
- **Date and Time:** Provides the current date and calculates future dates and times.
- **Local Processing:** Handles supported calculations and date/time requests directly in Python.

## Tech Stack

- Python
- Google Gemini API
- Google GenAI SDK
- JSON
- Regular Expressions

## Setup

1. Clone this repository.
2. Create and activate a virtual environment.
3. Install dependencies:

   `python -m pip install -r requirements.txt`

4. Create a `.env` file and add your Gemini API key:

   `GEMINI_API_KEY=your_api_key_here`

5. Run the agent:

   `python main.py`

## Security

API keys and personal memory files are stored locally and excluded from Git using `.gitignore`.

## Author

BTech Computer Science Student