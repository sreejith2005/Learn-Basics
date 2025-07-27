# NCERT Content Extractor

Extracts structured content from NCERT Class 8 Science PDFs and generates study planners using Google Gemini API.

## Features

- Downloads and parses NCERT Science textbook PDFs
- Extracts chapters, topics, subtopics, and content using AI
- Generates structured JSON and Excel outputs
- Creates customizable study planners (5-30 days)

## Requirements

pip install google-generativeai pandas openpyxl PyPDF2 requests

text

## Setup

1. Get a free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Replace `YOUR_GOOGLE_GEMINI_API_KEY` in the code with your actual key

## Usage

python solution.py

text

Enter study duration when prompted (5-30 days).

## Output Files

- `chapter_extract_TIMESTAMP.json` - Structured content extraction
- `science_content_TIMESTAMP.xlsx` - Excel format for validation
- `study_planner_Xdays_TIMESTAMP.xlsx` - Day-wise study schedule

## Supported Chapters

- Crop Production and Management
- Microorganisms: Friend and Foe
- Synthetic Fibres and Plastics
- Sound
