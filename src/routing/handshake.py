import re
import secrets
import string
from src.database.db import (
    save_pending_code,
    verify_and_consume_code,
    add_pairing,
    get_channel_id_for_gmail,
    get_gmails_for_channel
)

CODE_REGEX = re.compile(r"RELAY-[A-Z0-9]{4}")

def generate_code() -> str:
    """Generates a random code like 'RELAY-8X2P'."""
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"RELAY-{random_str}"

def handle_discord_command(discord_channel_id: str, message_text: str) -> dict:
    """
    Processes incoming messages from Discord channels.
    Returns an action dict specifying whether to reply with a system message or forward content.
    """
    text = message_text.strip()
    
    if text.startswith("!relay create"):
        code = generate_code()
        save_pending_code(code, discord_channel_id)
        return {
            "type": "system_reply",
            "content": f"🚨 *Disaster Relay Setup* 🚨\nPairing code generated: {code}\n\nHave the off-grid survivor send an email with subject/body containing {code} within 15 minutes to link their account."
        }
        
    elif text.startswith("!relay list"):
        gmails = get_gmails_for_channel(discord_channel_id)
        if not gmails:
            return {
                "type": "system_reply",
                "content": "No Gmail addresses are currently linked to this channel."
            }
        
        formatted_list = "\n".join([f"- {email}" for email in gmails])
        return {
            "type": "system_reply",
            "content": f"*Linked Gmail Accounts:*\n{formatted_list}"
        }

    # If it's not a system command, it's a message meant to be forwarded to all linked Gmails
    linked_gmails = get_gmails_for_channel(discord_channel_id)
    if not linked_gmails:
        return {
            "type": "ignore",
            "reason": "Channel has no linked Gmail accounts."
        }

    return {
        "type": "forward_to_gmail",
        "targets": linked_gmails,
        "content": text
    }


def handle_incoming_email(sender_email: str, subject: str, body: str) -> dict:
    """
    Processes incoming emails from Gmail.
    Checks for handshake codes first. If none exist, routes to linked Discord channels.
    """
    full_text = f"{subject} {body}".upper()
    match = CODE_REGEX.search(full_text)
    
    if match:
        code_found = match.group(0)
        target_channel_id = verify_and_consume_code(code_found)
        
        if target_channel_id:
            add_pairing(target_channel_id, sender_email)
            return {
                "type": "handshake_success",
                "target_channel_id": target_channel_id,
                "email_reply": f"Success! {sender_email} has been linked to the Discord disaster relay hub.",
                "discord_notification": f"✅ *Relay Established!* {sender_email} is now connected to this channel."
            }
        else:
            return {
                "type": "system_reply",
                "email_reply": f"Failed: Code '{code_found}' is either invalid or expired. Run '!relay create' in Discord to get a new code."
            }

    # If no code found, check if this email is already linked to one or more Discord channels
    target_channels = get_channel_id_for_gmail(sender_email)
    if not target_channels:
        return {
            "type": "unregistered",
            "email_reply": "Your email is not connected to a active disaster relay hub. Ask your hub admin to run '!relay create' in Discord."
        }

    formatted_payload = f"📩 *[RELAY via Gmail from {sender_email}]\nSubject:* {subject}\n\n{body}"
    
    return {
        "type": "forward_to_discord",
        "targets": target_channels,
        "content": formatted_payload
    }