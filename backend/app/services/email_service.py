"""email_service.py - sends the demo outreach email over real SMTP
(Gmail) when send-outreach is triggered. Same smtplib + STARTTLS pattern
already proven working in src/send_outreach_emails.py earlier this
project.

This is a fixed-address DEMO workflow, not per-salesperson delivery: the
salespersons table has no email column, so every send goes from one demo
sender to one demo recipient inbox, with the real salesperson/carrier
named in the body so the email still reads like a real handoff. If SMTP
isn't configured, send() returns an error instead of raising, so
send-outreach can still fall back to a simulated demo confirmation
rather than crashing the dashboard."""

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "demo-sender@example.com")
DEMO_TO_EMAIL = os.environ.get("DEMO_TO_EMAIL", "demo-recipient@example.com")


def is_configured() -> bool:
    return bool(SMTP_USERNAME and SMTP_APP_PASSWORD)


def send_outreach_email(carrier_name: str, salesperson_name: str, message: str):
    """Sends the outreach message as a real email. Returns (sent, error) -
    exactly one of which is None/False-y. Never raises."""
    if not is_configured():
        return False, "SMTP is not configured (missing SMTP_USERNAME/SMTP_APP_PASSWORD)."

    subject = f"Exploring New Sales Opportunities – {carrier_name}"
    body = f"{message}\n\nBest regards,\n{salesperson_name}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = DEMO_TO_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, f"Email send failed: {e}"
