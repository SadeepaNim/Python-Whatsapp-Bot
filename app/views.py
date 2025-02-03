import logging
import json

from flask import Blueprint, request, jsonify, current_app


from app.decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)


def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    try:
        # Parse the incoming JSON payload
        body = request.get_json(force=True)
        logging.info(f"Received request body: {json.dumps(body, indent=2)}")

        # Check if it's a WhatsApp status update
        if (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")
        ):
            logging.info("Received a WhatsApp status update.")
            return jsonify({"status": "ok"}), 200

        # Validate and process the WhatsApp message
        if is_valid_whatsapp_message(body):
            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            # If the request is not a WhatsApp API event, return an error
            logging.warning("Received an invalid WhatsApp API event.")
            return jsonify({"status": "error", "message": "Not a WhatsApp API event"}), 404
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400
    except Exception as e:
        logging.exception("An error occurred while handling the message")
        return jsonify({"status": "error", "message": str(e)}), 500


def verify():
    """
    Required webhook verification for WhatsApp.
    """
    try:
        # Parse parameters from the webhook verification request
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # Check if mode and token are provided
        if not mode or not token:
            logging.error("Missing parameters for verification")
            return jsonify({"status": "error", "message": "Missing parameters"}), 400

        # Validate the mode and token
        if mode == "subscribe" and token == current_app.config.get("VERIFY_TOKEN"):
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.warning("Verification failed: Invalid token or mode")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    except Exception as e:
        logging.exception("An error occurred during verification")
        return jsonify({"status": "error", "message": str(e)}), 500


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()


@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()
