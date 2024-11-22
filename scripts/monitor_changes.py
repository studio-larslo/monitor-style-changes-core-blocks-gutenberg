"""
Monitor changes between releases, focusing on specific file patterns:
1. folder: '/packages/block-editor/src'
2. pattern: '*.(s)css' or 'view.(m)js'
"""
from github import Github
import os
import re
import smtplib
from email.message import EmailMessage
import logging
from packaging import version

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

def get_latest_releases(repo, count=2):
    """Get the latest releases from the repository"""
    logger.info("Fetching latest releases...")
    releases = repo.get_releases()
    # Convert to list and sort by version
    releases_list = list(releases[:count+5])  # Fetch extra to ensure we have valid releases
    valid_releases = [r for r in releases_list if not r.prerelease]  # Filter out pre-releases
    valid_releases.sort(key=lambda x: version.parse(x.tag_name), reverse=True)
    return valid_releases[:count]

def check_file_changes(repo, base_tag, head_tag):
    """Compare two releases and check for relevant file changes"""
    logger.info(f"Comparing releases: {base_tag} → {head_tag}")
    
    comparison = repo.compare(base_tag, head_tag)
    matching_files = []
    
    for file in comparison.files:
        if re.search(pattern1, file.filename):
            if re.search(pattern2, file.filename):
                logger.info(f"Match found: {file.filename}")
                matching_files.append({
                    'filename': file.filename,
                    'status': file.status,
                    'changes': file.changes
                })
    
    return matching_files

def format_email_content(matching_files, comparison_url, latest_release):
    """Format the email content with the changes"""
    content = f"New Release: {latest_release.tag_name}\n"
    content += f"Released on: {latest_release.created_at}\n\n"
    content += "Relevant file changes:\n\n"
    
    # Group files by status
    added = [f for f in matching_files if f['status'] == 'added']
    modified = [f for f in matching_files if f['status'] == 'modified']
    removed = [f for f in matching_files if f['status'] == 'removed']
    
    if added:
        content += "Added Files:\n"
        for file in added:
            content += f"+ {file['filename']}\n"
        content += "\n"
    
    if modified:
        content += "Modified Files:\n"
        for file in modified:
            content += f"~ {file['filename']} ({file['changes']} changes)\n"
        content += "\n"
    
    if removed:
        content += "Removed Files:\n"
        for file in removed:
            content += f"- {file['filename']}\n"
        content += "\n"
    
    content += f"\nFull comparison: {comparison_url}"
    return content

def send_notification(content):
    """Send email notification with the changes"""
    logger.info(f"Sending notification email to: {receiver_email}")
    msg = EmailMessage()
    msg.set_content(content)
    
    msg['Subject'] = 'Gutenberg Release Change Alert'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, email_password)
            server.send_message(msg)
            logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

def main():
    logger.info(f"Starting release monitoring for: {target_repo}")
    g = Github(github_token)
    repo = g.get_repo(target_repo)
    
    # Get latest releases
    releases = get_latest_releases(repo)
    if len(releases) < 2:
        logger.info("Not enough releases to compare")
        return
    
    latest = releases[0]
    previous = releases[1]
    
    # Check for relevant changes
    matching_files = check_file_changes(repo, previous.tag_name, latest.tag_name)
    
    if matching_files:
        logger.info(f"Found {len(matching_files)} relevant changes")
        content = format_email_content(
            matching_files,
            f"https://github.com/{target_repo}/compare/{previous.tag_name}...{latest.tag_name}",
            latest
        )
        send_notification(content)
    else:
        logger.info("No relevant changes found")

if __name__ == "__main__":
    main()

