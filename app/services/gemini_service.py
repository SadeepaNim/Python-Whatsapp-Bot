# app/services/gemini_service.py

import google.generativeai as genai
import os

# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Function to generate response from Gemini
def generate_response(message_body, wa_id, name):
    """
    Generate a response from Gemini API based on the incoming message.
    """
    # Set up the configuration for the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    # Instantiate the model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",  # Ensure the model name is correct (example: gemini-1.5-pro)
        generation_config=generation_config,
    )

    # Create a chat session (history is empty as we're starting fresh)
    chat_session = model.start_chat(history=[])

    # Send the user's message to Gemini for a response
    response = chat_session.send_message(message_body)

    # Return the generated response text
    return response.text
