from github import Github
import os
import re
import smtplib
from email.message import EmailMessage

# GitHub configuration
github_token = os.environ['MONITOR_TOKEN']
target_repo = "WordPress/gutenberg"
pattern = r'packages/block-library/src/.*\.scss$'  # Matches SCSS files in any subfolder under src/


# Email configuration
smtp_server = os.environ['SMTP_SERVER']
smtp_port = 587
sender_email = os.environ['SENDER_EMAIL']
receiver_email = os.environ['RECEIVER_EMAIL']
email_password = os.environ['EMAIL_PASSWORD']

def check_changes():
    g = Github(github_token)
    repo = g.get_repo(target_repo)
    
    # Get latest commits
    commits = repo.get_commits()
    latest_commit = commits[0]
    
    # Check modified files
    matching_files = []
    for file in latest_commit.files:
        if re.search(pattern, file.filename):
            matching_files.append(file.filename)
    
    if matching_files:
        send_notification(matching_files, latest_commit)

def send_notification(files, commit):
    msg = EmailMessage()
    msg.set_content(f"Changes detected in files:\n\n" + 
                    "\n".join(files) + 
                    f"\n\nCommit: {commit.html_url}")
    
    msg['Subject'] = 'Repository Change Alert'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, email_password)
        server.send_message(msg)

if __name__ == "__main__":
    check_changes()
