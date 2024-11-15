from email.message import EmailMessage
import smtplib
import os

# Email configuration
smtp_server = os.environ['SMTP_SERVER']
smtp_port = 587
sender_email = os.environ['SENDER_EMAIL']
receiver_email = os.environ['RECEIVER_EMAIL']
email_password = os.environ['EMAIL_PASSWORD']

def send_test_email():
    msg = EmailMessage()
    msg.set_content("This is a test email from the monitoring system.")
    
    msg['Subject'] = 'Test Email - Repository Monitor'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, email_password)
        server.send_message(msg)

if __name__ == "__main__":
    send_test_email()
