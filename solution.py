import google.generativeai as genai
import json
import pandas as pd
import PyPDF2
import requests
from io import BytesIO
import os
from datetime import datetime
import re

class NCERTExtractor:
    def __init__(self, api_key):
        """Initialize with Google Gemini API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def download_pdf(self, url):
        """Download PDF from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            print(f"Error downloading PDF from {url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_url):
        """Extract text from PDF URL"""
        pdf_file = self.download_pdf(pdf_url)
        if not pdf_file:
            return ""
            
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def chunk_text(self, text, max_chars=6000):
        """Split text into manageable chunks for API"""
        if not text.strip():
            return []
            
        chunks = []
        words = text.split()
        current_chunk = ""
        
        for word in words:
            if len(current_chunk + word) < max_chars:
                current_chunk += word + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = word + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        return chunks
    
    def clean_json_response(self, response_text):
        """Clean and extract JSON from API response"""
        if not response_text:
            return None
        
        # Remove markdown code blocks - PROPERLY FIXED
        # remove any ``````json fences
        response_text = response_text.replace('``````', "")
        response_text = response_text.replace('```', '')
        response_text = response_text.strip()
        
        # Try to find JSON in the response
        json_patterns = [
            r'\{.*\}',  # Find JSON object
            r'\[.*\]'   # Find JSON array
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found, try the whole response
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            return None

    
    def extract_content_with_prompt(self, text_chunk, chapter_name=""):
        """Execute the content extraction prompt with better error handling"""
        extraction_prompt = f"""
Extract and structure content from this Class 8 NCERT Science chapter text. Return ONLY valid JSON, no explanations.

Text: {text_chunk[:4000]}...

Required JSON format:
{{
  "chapter_number": "detect from text",
  "chapter_name": "{chapter_name}",
  "topics": [
    {{
      "topic_name": "main heading from text",
      "sub_topics": [
        {{
          "sub_topic_name": "sub heading",
          "content": [
            {{
              "type": "paragraph",
              "title_or_caption": "",
              "data_or_text": "actual text content"
            }}
          ]
        }}
      ]
    }}
  ]
}}

Extract topics, sub-topics, paragraphs, activities, images, tables, and questions as they appear. Return only the JSON structure.
"""
        
        try:
            response = self.model.generate_content(extraction_prompt)
            if response and response.text:
                return self.clean_json_response(response.text)
            return None
        except Exception as e:
            print(f"Error in content extraction: {e}")
            return None
    
    def create_study_planner(self, json_data, study_days):
        """Execute the study planner generation prompt"""
        # Simplify the data for the planner prompt
        simplified_data = []
        for chapter in json_data:
            chapter_info = {
                "chapter_name": chapter.get("chapter_name", ""),
                "topics": [topic.get("topic_name", "") for topic in chapter.get("topics", [])]
            }
            simplified_data.append(chapter_info)
        
        planner_prompt = f"""
Create a {study_days}-day study plan for these chapters. Return ONLY valid JSON array, no explanations.

Chapters: {json.dumps(simplified_data, indent=2)}

Required JSON format:
[
  {{
    "day": 1,
    "chapters": ["Chapter Name"],
    "topics_subtopics": ["Topic 1", "Topic 2"],
    "activities": ["Reading", "Exercises"],
    "estimated_hours": 2,
    "notes_space": ""
  }}
]

Distribute all topics across {study_days} days logically. Return only the JSON array.
"""
        
        try:
            response = self.model.generate_content(planner_prompt)
            if response and response.text:
                return self.clean_json_response(response.text)
            return None
        except Exception as e:
            print(f"Error in planner generation: {e}")
            return None
    
    def process_all_chapters(self, pdf_urls, chapter_names):
        """Process all chapters and create outputs"""
        all_extracted_data = []
        
        for i, (url, chapter_name) in enumerate(zip(pdf_urls, chapter_names)):
            print(f"Processing Chapter {i+1}: {chapter_name}")
            
            # Extract text from PDF
            text = self.extract_text_from_pdf(url)
            if not text.strip():
                print(f"No text extracted from {chapter_name}")
                continue
                
            chunks = self.chunk_text(text)
            print(f"Created {len(chunks)} chunks for {chapter_name}")
            
            # Process each chunk
            for j, chunk in enumerate(chunks):
                print(f"Processing chunk {j+1}/{len(chunks)} for {chapter_name}")
                extracted = self.extract_content_with_prompt(chunk, chapter_name)
                
                if extracted:
                    all_extracted_data.append(extracted)
                    print(f"[SUCCESS] Successfully processed chunk {j+1}")
                else:
                    print(f"[FAILED] Failed to process chunk {j+1}")
        
        return all_extracted_data
    
    def save_to_files(self, extracted_data, study_days=10):
        """Save extracted data to JSON, Excel, and create study planner"""
        if not extracted_data:
            print("No data to save!")
            return None, None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_filename = f"chapter_extract_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] JSON saved: {json_filename}")
        
        # Create Excel
        excel_filename = f"science_content_{timestamp}.xlsx"
        self.create_excel_from_json(extracted_data, excel_filename)
        
        # Create Study Planner
        planner_data = self.create_study_planner(extracted_data, study_days)
        if planner_data:
            planner_filename = f"study_planner_{study_days}days_{timestamp}.xlsx"
            self.create_planner_excel(planner_data, planner_filename)
        
        return json_filename, excel_filename
    
    def create_excel_from_json(self, data, filename):
        """Convert JSON to structured Excel"""
        rows = []
        for chapter in data:
            chapter_name = chapter.get('chapter_name', 'Unknown Chapter')
            chapter_num = chapter.get('chapter_number', '')
            
            for topic in chapter.get('topics', []):
                topic_name = topic.get('topic_name', '')
                
                for subtopic in topic.get('sub_topics', []):
                    subtopic_name = subtopic.get('sub_topic_name', '')
                    
                    for content in subtopic.get('content', []):
                        rows.append({
                            'Chapter_Number': chapter_num,
                            'Chapter_Name': chapter_name,
                            'Topic': topic_name,
                            'Sub_Topic': subtopic_name,
                            'Content_Type': content.get('type', ''),
                            'Title_Caption': content.get('title_or_caption', ''),
                            'Content_Data': content.get('data_or_text', '')
                        })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_excel(filename, index=False)
            print(f"[SUCCESS] Excel file created: {filename}")
        else:
            print("[ERROR] No data to create Excel file")
    
    def create_planner_excel(self, planner_data, filename):
        """Create study planner Excel"""
        if planner_data:
            df = pd.DataFrame(planner_data)
            df.to_excel(filename, index=False)
            print(f"[SUCCESS] Study planner created: {filename}")
        else:
            print("[ERROR] No planner data to save")

# Main execution function
def main():
    # Set your Google API key here
    API_KEY = "AIzaSyATdfsyhOsadsadaGUvnigaMK9mdHEA"  # Replace with your actual API key
    
    if API_KEY == "":
        print("[ERROR] Please set your Google Gemini API key in the API_KEY variable")
        return
    
    # NCERT PDF URLs
    pdf_urls = [
        "https://ncert.nic.in/textbook/pdf/hesc106.pdf",
        "https://ncert.nic.in/textbook/pdf/hesc107.pdf", 
        "https://ncert.nic.in/textbook/pdf/hesc108.pdf",
        "https://ncert.nic.in/textbook/pdf/hesc113.pdf"
    ]
    
    chapter_names = [
        "Crop Production and Management",
        "Microorganisms: Friend and Foe", 
        "Synthetic Fibres and Plastics",
        "Sound"
    ]
    
    # Initialize extractor
    extractor = NCERTExtractor(API_KEY)
    
    # Process all chapters
    print("Starting content extraction...")
    extracted_data = extractor.process_all_chapters(pdf_urls, chapter_names)
    
    if not extracted_data:
        print("[ERROR] No data extracted. Please check your API key and internet connection.")
        return
    
    # Get study duration from user
    try:
        study_days = int(input("Enter number of study days (5-30): "))
        if study_days < 5 or study_days > 30:
            study_days = 10
            print("Invalid input. Using default 10 days.")
    except ValueError:
        study_days = 10
        print("Invalid input. Using default 10 days.")
    
    # Save outputs
    json_file, excel_file = extractor.save_to_files(extracted_data, study_days)
    
    print(f"\n[COMPLETED] Task completed successfully!")
    print(f"JSON output: {json_file}")
    print(f"Excel output: {excel_file}")

if __name__ == "__main__":
    main()
