"""send_outreach_emails.py - the automated outreach step: finds
unsent notifications for still-open opportunities and emails each
assigned rep directly. This is what turns "the agent can generate an
outreach message" into "the system actually notifies the right people" -
the gap flagged in the TR1 review.

Multiple reps can be notified for the same opportunity (Sampath's "10 reps
get emailed, whoever claims first wins" scenario) - each gets their own
notifications row and their own email. Once ANYONE claims the opportunity
(status becomes 'closed'), this script skips any of that opportunity's
remaining unsent notifications - matching "whoever's first wins."
"""

import os
import sys
import smtplib
import sqlite3
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

DB_PATH = "sales_opportunities.db"

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_APP_PASSWORD = os.environ["SMTP_APP_PASSWORD"]
FROM_EMAIL = os.environ["FROM_EMAIL"]

OUTREACH_TEMPLATE = (
    "Hi {salesperson_name},\n\n"
    "A new out-of-service opportunity was just identified in your territory:\n\n"
    "  Carrier: {legal_name}\n"
    "  Location: {phy_city}, {phy_state}\n"
    "  Out-of-service date: {oos_date}\n"
    "  Reason: {oos_reason}\n\n"
    "Suggested outreach message to the carrier:\n"
    '  "Hi {legal_name}, I see your operations were recently impacted by an '
    'out-of-service notice dated {oos_date}. Can we set up a call to discuss '
    'new sales opportunities?"\n\n'
    "Note: other reps in your region may also be notified about this same "
    "opportunity - whoever reaches out and claims it first on the dashboard "
    "gets it."
)


def get_pending_notifications(conn, limit=None):
    query = """
        SELECT n.id, n.dot_number, n.salesperson_name, n.salesperson_email,
               o.legal_name, o.oos_date, o.oos_reason, o.phy_city, o.phy_state
        FROM notifications n
        JOIN opportunities o ON o.dot_number = n.dot_number
        WHERE n.sent_at IS NULL AND o.status = 'open'
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return conn.execute(query).fetchall()


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
        server.sendmail(FROM_EMAIL, [to_email], msg.as_string())


def main(limit=None):
    conn = sqlite3.connect(DB_PATH)
    rows = get_pending_notifications(conn, limit=limit)
    print(f"Found {len(rows)} pending notifications to send" + (f" (limited to {limit})" if limit else "") + ".")

    sent = 0
    for row in rows:
        (notif_id, dot_number, salesperson_name, salesperson_email,
         legal_name, oos_date, oos_reason, phy_city, phy_state) = row

        body = OUTREACH_TEMPLATE.format(
            salesperson_name=salesperson_name, legal_name=legal_name,
            phy_city=phy_city, phy_state=phy_state, oos_date=oos_date,
            oos_reason=oos_reason,
        )
        subject = f"New OOS opportunity: {legal_name} ({phy_state})"

        try:
            send_email(salesperson_email, subject, body)
            conn.execute("UPDATE notifications SET sent_at = datetime('now') WHERE id = ?", (notif_id,))
            conn.commit()
            sent += 1
            print(f"  emailed {salesperson_name} <{salesperson_email}> re: {legal_name} ({phy_state})")
        except Exception as e:
            print(f"  FAILED to email {salesperson_email} re: {legal_name}: {e}")

    conn.close()
    print(f"Done. Sent {sent} of {len(rows)} emails.")


if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=limit_arg)
