# Enterprise Multi-Agent AI Research Automation System

An AI-powered research application built with Python, Streamlit, and Google Gemini API. It uses specialized AI agents to generate research overviews, summaries, and structured reports.

## Features

- **Research Agent:** Generates detailed research overviews.
- **Summarization Agent:** Produces clear, concise summaries.
- **Report Generation Agent:** Creates structured research reports.
- **SQLite Database:** Stores generated research history locally.
- **Report Download:** Downloads generated reports as text files.
- **Interactive Interface:** Provides a simple Streamlit web application.

## Technologies Used

- Python
- Streamlit
- Google Gemini API
- SQLite
- python-dotenv

## Project Structure

```text
Enterprise-Multi-Agent-AI-Research-Automation-System/
├── app.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
└── research_history.db  # Created automatically
```

## Installation

1. Clone this repository or download the project.
2. Install the required packages:

   `python -m pip install -r requirements.txt`

3. Create a `.env` file in the project root and add your Gemini API key:

   `GEMINI_API_KEY=your_actual_api_key`

4. Run the application:

   `python -m streamlit run app.py`

5. Open the local URL displayed in your terminal.

## Security

Never commit API keys, `.env` files, or private credentials to GitHub.

## Limitations

Generated research may contain inaccurate information. Verify important facts and references independently. The application does not automatically verify live web sources.

## License

This project is intended for educational and portfolio use. See the repository's LICENSE file for applicable terms.
