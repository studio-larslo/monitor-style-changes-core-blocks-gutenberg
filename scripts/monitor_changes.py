"""
Goal of this workflow is to monitor frontend changes of core gutenberg blocks
since these might directly affect the frontend of the website 
and therefore need to be monitored.
lets watch the '/packages/block-editor/src' subfolders 
here we focus on '*.(s)css' and 'view.(m)js' files
lets do it with two patterns
1. folder: '/packages/block-editor/src'
2. pattern: '*.(s)css' or 'view.(m)js'
"""
from github import Github
import os
import re
import smtplib
from email.message import EmailMessage
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub configuration
github_token = os.environ['MONITOR_TOKEN']
target_repo = "WordPress/gutenberg"
pattern1 = r'packages/block-editor/src/'
pattern2 = r'\.(s)css|view\.(m)js'

# Email configuration
smtp_server = os.environ['SMTP_SERVER']
smtp_port = 587
sender_email = os.environ['SENDER_EMAIL']
receiver_email = os.environ['RECEIVER_EMAIL']
email_password = os.environ['EMAIL_PASSWORD']

def check_changes():
    logger.info(f"Starting repository check for: {target_repo}")
    g = Github(github_token)
    repo = g.get_repo(target_repo)
    
    logger.info("Fetching latest commits...")
    commits = repo.get_commits()
    latest_commit = commits[0]
    logger.info(f"Latest commit: {latest_commit.sha}")
    
    matching_files = []
    logger.info("Checking modified files...")
    for file in latest_commit.files:
        if re.search(pattern1, file.filename):
            if re.search(pattern2, file.filename):
                logger.info(f"Match found: {file.filename}")
                matching_files.append(file.filename)
    
    if matching_files:
        logger.info(f"Found {len(matching_files)} matching files")
        send_notification(matching_files, latest_commit)
    else:
        logger.info("No matching files found")

def send_notification(files, commit):
    logger.info(f"Sending notification email to: {receiver_email}")
    msg = EmailMessage()
    msg.set_content(f"Changes detected in files:\n\n" + 
                    "\n".join(files) + 
                    f"\n\nCommit: {commit.html_url}")
    
    msg['Subject'] = 'Repository Change Alert'
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
    check_changes()
