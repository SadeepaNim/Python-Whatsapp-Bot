import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.services.gemini_service import generate_response



def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    """
    Generate the payload for sending a WhatsApp text message.
    """
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    """
    Send a WhatsApp message via the Meta Graph API.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending the message.")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    """
    Format the text for WhatsApp style, converting **bold** to *bold*.
    """
    # Remove text within 【 and 】
    text = re.sub(r"【.*?】", "", text).strip()

    # Convert **bold** to *bold*
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)

    return text


def process_whatsapp_message(body):
    """
    Process an incoming WhatsApp message and generate a response using Gemini API.
    """
    try:
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_body = message["text"]["body"]

        # Generate a response using Gemini service
        gemini_response = generate_response(message_body, wa_id, name)
        whatsapp_formatted_response = process_text_for_whatsapp(gemini_response)

        # Prepare and send the response
        data = get_text_message_input(wa_id, whatsapp_formatted_response)
        send_message(data)

    except KeyError as e:
        logging.error(f"KeyError: Missing key in WhatsApp message body - {e}")
        return jsonify({"status": "error", "message": "Invalid message structure"}), 400
    except Exception as e:
        logging.error(f"Error processing WhatsApp message: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


def is_valid_whatsapp_message(body):
    """
    Validate the structure of an incoming WhatsApp message webhook event.
    """
    try:
        return (
            body.get("object")
            and body.get("entry")
            and body["entry"][0].get("changes")
            and body["entry"][0]["changes"][0].get("value")
            and body["entry"][0]["changes"][0]["value"].get("messages")
            and body["entry"][0]["changes"][0]["value"]["messages"][0]
        )
    except (KeyError, TypeError) as e:
        logging.error(f"Validation error: {e}")
        return False
