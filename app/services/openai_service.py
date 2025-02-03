import logging
from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI(api_key=OPENAI_API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_if_thread_exists(wa_id):
    """
    Check if a thread exists for the given WhatsApp ID.
    """
    with shelve.open("threads_db") as threads_shelf:
        thread = threads_shelf.get(wa_id, None)
        if thread:
            logging.info(f"Thread found for wa_id {wa_id}: {thread}")
        else:
            logging.info(f"No thread found for wa_id {wa_id}")
        return thread

def store_thread(wa_id, thread_id):
    """
    Store the thread ID associated with the given WhatsApp ID.
    """
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id
        logging.info(f"Stored thread ID {thread_id} for wa_id {wa_id}")

def run_assistant(thread_id, name):
    """
    Execute the assistant on the specified thread and return the generated response.
    """
    try:
        # Retrieve the assistant
        assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)
        logging.info(f"Assistant retrieved: {assistant.id}")

        # Start a new run for the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant.id,
        )
        logging.info(f"Started run for thread {thread_id}")

        # Poll for run completion
        while run.status != "completed":
            logging.info(f"Run status: {run.status}")
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        # Retrieve the latest messages in the thread
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        logging.info(f"Messages fetched: {messages.data}")  # Log raw messages data

        if messages.data:
            # Returning the assistant's generated response instead of just the last sent message
            for message in messages.data:
                if message.role == 'assistant':  # Looking for the assistant's response
                    return message.content[0].text.value
            logging.error("No assistant message found in the thread.")
            return "I couldn't generate a response. Please try again."
        else:
            logging.error("No messages found in the thread after assistant run.")
            return "I couldn't generate a response. Please try again."
    except Exception as e:
        logging.error(f"Error during assistant execution: {e}")
        return "An error occurred while processing your request."

def generate_response(message_body, wa_id, name):
    """
    Generate a response for the incoming WhatsApp message using OpenAI's Assistant API.
    """
    try:
        # Check if a thread exists for the wa_id
        thread_id = check_if_thread_exists(wa_id)

        # If no thread exists, create one
        if thread_id is None:
            logging.info(f"No thread found for wa_id {wa_id}. Creating a new thread.")
            try:
                thread = client.beta.threads.create()
                store_thread(wa_id, thread.id)
                thread_id = thread.id
            except Exception as create_error:
                logging.error(f"Failed to create a new thread for wa_id {wa_id}: {create_error}")
                return "An error occurred while setting up your conversation. Please try again."
        else:
            logging.info(f"Retrieved existing thread ID {thread_id} for wa_id {wa_id}")
            try:
                # Verify thread exists
                thread = client.beta.threads.retrieve(thread_id)
            except Exception as retrieve_error:
                logging.warning(f"Thread ID {thread_id} for wa_id {wa_id} is invalid. Creating a new thread.")
                thread = client.beta.threads.create()
                store_thread(wa_id, thread.id)
                thread_id = thread.id

        # Add the incoming message to the thread
        logging.info(f"Adding message to thread {thread_id}: {message_body}")
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_body,
        )

        # Generate a response using the assistant
        return run_assistant(thread_id, name)
    except Exception as e:
        logging.error(f"Error processing WhatsApp message: {e}")
        return "An error occurred while generating a response. Please try again."

# Optional utility for logging HTTP response (if needed for debugging API requests)
def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")
