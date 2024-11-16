
"""
send a test email to check if the email setup is working
run via github webinterface -> actions -> workflows -> run workflow
needs 
gh secrets to be set before
like this
gh secret SMTP_SERVER=smtp.gmail.com
"""
from email.message import EmailMessage
import smtplib
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration
smtp_server = os.environ['SMTP_SERVER']
smtp_port = 587
sender_email = os.environ['SENDER_EMAIL']
receiver_email = os.environ['RECEIVER_EMAIL']
email_password = os.environ['EMAIL_PASSWORD']

def send_test_email():
    logger.info(f"Starting email test with server: {smtp_server}")
    logger.info(f"Sending from: {sender_email} to: {receiver_email}")
    
    msg = EmailMessage()
    msg.set_content("This is a test email from the monitoring system.")
    
    msg['Subject'] = 'Test Email - Repository Monitor'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info("Connecting to SMTP server...")
            server.starttls()
            logger.info("Starting TLS...")
            server.login(sender_email, email_password)
            logger.info("Logged in successfully")
            server.send_message(msg)
            logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

if __name__ == "__main__":
    send_test_email()
