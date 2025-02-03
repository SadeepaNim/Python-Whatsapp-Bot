import os
import requests
import google.generativeai as genai
import shelve
from dotenv import load_dotenv
import PyPDF2  # To extract text from PDF files
import time

# Load API keys
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# --------------------------------------------------------------
# Initialize the model configuration
# --------------------------------------------------------------
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
)

# --------------------------------------------------------------
# Extract text from PDF file
# --------------------------------------------------------------
def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file using PyPDF2.
    """
    try:
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {e}")

# Example: Replace with the path to your local PDF file
file_path = "c:/Users/Sadeepa's/python-whatsapp-bot-main/data/AirbnbFAQ.pdf"
try:
    pdf_content = extract_text_from_pdf(file_path)
    print("PDF content extracted successfully.")
except Exception as e:
    print(f"Error: {e}")

# --------------------------------------------------------------
# Chat session management
# --------------------------------------------------------------
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, session_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = session_id

# --------------------------------------------------------------
# Generate response
# --------------------------------------------------------------
def generate_response(message_body, wa_id, name):
    # Check if there's already a session for the user
    session_id = check_if_thread_exists(wa_id)
    
    # If no session exists, create one
    if session_id is None:
        print(f"Creating new chat session for {name} with wa_id {wa_id}")
        chat_session = model.start_chat(history=[
            {"role": "system", "content": "You are a helpful assistant. Refer to the following content for context:"},
            {"role": "system", "content": pdf_content},  # Add PDF content as context
        ])
        store_thread(wa_id, chat_session.session_id)
        session_id = chat_session.session_id
    else:
        print(f"Retrieving existing chat session for {name} with wa_id {wa_id}")
        chat_session = model.get_chat_session(session_id)
    
    # Send message to the assistant
    response = chat_session.send_message(message_body)
    print(f"To {name}: {response.text}")
    return response.text

# --------------------------------------------------------------
# Test assistant
# --------------------------------------------------------------
new_message = generate_response("What's the check-in time?", "123", "John")
new_message = generate_response("What's the pin for the lockbox?", "456", "Sarah")
new_message = generate_response("What was my previous question?", "123", "John")
new_message = generate_response("What was my previous question?", "456", "Sarah")
