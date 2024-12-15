"""
Monitor changes between releases with test mode support
"""
from github import Github
import os
import re
import logging
from packaging import version
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_specific_releases(repo, base_tag=None, head_tag=None):
    """Get specific releases for testing"""
    logger.info(f"Fetching specific releases: {base_tag} → {head_tag}")
    if base_tag and head_tag:
        try:
            # Add 'v' prefix if not present
            base_tag = f"v{base_tag}" if not base_tag.startswith('v') else base_tag
            head_tag = f"v{head_tag}" if not head_tag.startswith('v') else head_tag
            
            try:
                base_release = repo.get_release(base_tag)
                head_release = repo.get_release(head_tag)
                return [head_release, base_release]
            except Exception as e:
                # Try without 'v' prefix if first attempt fails
                base_tag = base_tag[1:] if base_tag.startswith('v') else base_tag
                head_tag = head_tag[1:] if head_tag.startswith('v') else head_tag
                base_release = repo.get_release(base_tag)
                head_release = repo.get_release(head_tag)
                return [head_release, base_release]
                
        except Exception as e:
            logger.error(f"Error fetching specific releases: {e}")
            # List available releases for debugging
            releases = list(repo.get_releases()[:5])
            logger.info("Available recent releases:")
            for release in releases:
                logger.info(f"- {release.tag_name}")
            return []
    return get_latest_releases(repo)

def get_latest_releases(repo, count=2):
    """Get the latest releases from the repository"""
    logger.info("Fetching latest releases...")
    releases = repo.get_releases()
    releases_list = list(releases[:count+5])
    valid_releases = [r for r in releases_list if not r.prerelease]
    valid_releases.sort(key=lambda x: version.parse(x.tag_name), reverse=True)
    return valid_releases[:count]

def check_file_changes(repo, base_tag, head_tag):
    """Compare two releases using GitHub's comparison API and filter for specific patterns"""
    logger.info(f"Comparing releases: {base_tag} → {head_tag}")
    
    WATCHED_FOLDER = 'packages/block-library/src'
    WATCHED_PATTERNS = r'(view\.js|block\.json|style\.(s)?css|save\.js|index\.php)'
    
    comparison = repo.compare(base_tag, head_tag)
    logger.info(f"Comparison URL: {comparison.html_url}")    
    comparison = repo.compare(base_tag, head_tag)
    logger.info(f"Comparison URL: {comparison.html_url}")
    
    changed_files = []
    for file in comparison.files:
        if (file.filename.startswith(WATCHED_FOLDER) and 
            (re.search(WATCHED_PATTERNS, file.filename) or 
             'view' in file.filename.lower())):
            # Create a deterministic hash from the filename
            file_hash = hashlib.sha256(file.filename.encode()).hexdigest()
            changed_files.append({
                'filename': file.filename,
                'status': file.status,
                'changes': file.changes,
                'hash': file_hash
            })
            logger.info(f"Matched file: {file.filename}")
    
    return changed_files, comparison.html_url

def format_changes_report(files, comparison_url, latest_release):
    """Format the changes report"""
    report = f"# Release Comparison Report\n\n"
    report += f"New Release: {latest_release.tag_name}\n"
    report += f"Released on: {latest_release.created_at}\n\n"
    
    # Group files by status
    added = [f for f in files if f['status'] == 'added']
    modified = [f for f in files if f['status'] == 'modified']
    removed = [f for f in files if f['status'] == 'removed']
    
    report += f"## Summary\n"
    report += f"- Added: {len(added)} files\n"
    report += f"- Modified: {len(modified)} files\n"
    report += f"- Removed: {len(removed)} files\n\n"
    
    # Part 1: Simple list of filenames
    report += "## Changed Files (Overview)\n"
    
    if added:
        report += "\n### Added:\n"
        for file in added:
            report += f"- {file['filename']}\n"
    
    if modified:
        report += "\n### Modified:\n"
        for file in modified:
            report += f"- {file['filename']} ({file['changes']} changes)\n"
    
    if removed:
        report += "\n### Removed:\n"
        for file in removed:
            report += f"- {file['filename']}\n"
    
    # Part 2: How to use links
    report += "\n## Detailed Changes (with links)\n"
    report += "How to use: Click on 'Files changed' and and wait for second (page might be huge)\n\n"
    
    if added:
        report += "### Added Files:\n"
        for file in added:
            file_url = f"{comparison_url}/#diff-{file['hash']}"
            report += f"{file['filename']}:\n[View changes]({file_url})\n\n"
    
    if modified:
        report += "### Modified Files:\n"
        for file in modified:
            file_url = f"{comparison_url}/#diff-{file['hash']}"
            report += f"{file['filename']}:\n[View changes]({file_url})\n\n"
    
    if removed:
        report += "### Removed Files:\n"
        for file in removed:
            file_url = f"{comparison_url}/#diff-{file['hash']}"
            report += f"{file['filename']}:\n[View changes]({file_url})\n\n"
    
    report += f"[View full comparison on GitHub]({comparison_url}?diff=unified&w=1&expand=0)"
    
    return report

def send_email(report, latest_tag, previous_tag):
    """Send email with the changes report"""
    logger.info("Preparing to send email...")
    
    smtp_server = os.environ['SMTP_SERVER']
    sender_email = os.environ['SENDER_EMAIL']
    receiver_email = os.environ['RECEIVER_EMAIL']
    password = os.environ['EMAIL_PASSWORD']

    # Create message
    message = MIMEMultipart()
    message["Subject"] = f"Watching Gutenberg Changes: {previous_tag} → {latest_tag}"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Add body
    message.attach(MIMEText(report, "markdown"))

    try:
        # Create secure SSL/TLS connection
        server = smtplib.SMTP(smtp_server, 587)
        server.starttls()
        server.login(sender_email, password)
        
        # Send email
        server.send_message(message)
        logger.info("Email sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
    finally:
        server.quit()


def update_version_history_as_release(repo, latest_tag, previous_tag, has_changes, report):
    """Create a release note to track the comparison"""
    from datetime import datetime
    
    g = Github(os.environ.get('MONITOR_TOKEN'))
    monitor_repo = g.get_repo(os.environ.get('GITHUB_REPOSITORY'))
    
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    title = f"Comparison {previous_tag} → {latest_tag}"
    
    # Use the full report as release description
    monitor_repo.create_git_release(
        tag=f"comparison-{latest_tag}-{timestamp}",
        name=title,
        message=report,
        draft=False,
        prerelease=False,
        generate_release_notes=False
    )


def has_comparison_release(repo, latest_tag):
    """Check if comparison already exists"""
    comparison_tag = f"comparison-{latest_tag}"
    logger.info(f"Checking for comparison tag: {comparison_tag} in repo: {repo.full_name}")
    try:
        repo.get_release(comparison_tag)
        return True
    except:
        return False

def has_comparison_release(repo, latest_tag):
    """Check if a comparison release already exists based on tag prefix."""
    releases = repo.get_releases()
    comparison_prefix = f"comparison-{latest_tag}"
    for release in releases:
        if release.tag_name.startswith(comparison_prefix):
            return True
    return False
   

def main():
    # Get configuration from environment
    github_token = os.environ.get('MONITOR_TOKEN')
    # target_repo = os.environ.get('TARGET_REPO', 'WordPress/gutenberg')
    target_repo = 'WordPress/gutenberg'
    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    base_tag = os.environ.get('BASE_TAG')
    head_tag = os.environ.get('HEAD_TAG')
    
    logger.info(f"Starting release monitoring for: {target_repo}")
    logger.info(f"Test mode: {test_mode}")
    
    try:
        g = Github(github_token)
        # Test the authentication
        logger.info(f"Attempting to access repository: {target_repo}")
        user = g.get_user()
        logger.info(f"Authenticated as: {user.login}")
        repo = g.get_repo(target_repo)
        logger.info(f"Repository accessed: {repo.full_name}")
        
    except Exception as e:
        logger.error(f"GitHub Authentication Error: {e}")
        logger.error("Please check your MONITOR_TOKEN permissions")
        logger.error("Token needs: repo access (public_repo for public repositories)")
        # send email to myself
        send_email("GitHub Authentication Error: " + str(e), "GitHub Authentication Error")
        return
    
    # Get releases based on mode
    if test_mode:
        releases = get_specific_releases(repo, base_tag, head_tag)
    else:
        releases = get_latest_releases(repo)
    
    if len(releases) < 2:
        logger.error("Not enough releases to compare")
        return
    
    latest = releases[0]
    previous = releases[1]
    self_repo = g.get_repo('studio-larslo/monitor-style-changes-core-blocks-gutenberg')
    
    # Check if comparison already exists first
    if has_comparison_release(self_repo, latest.tag_name):
        logger.info(f"Comparison between {previous.tag_name} and {latest.tag_name} already exists. Exiting.")
        return
    
    # Check for changes before creating release
    matching_files, comparison_url = check_file_changes(repo, previous.tag_name, latest.tag_name)
    
    if matching_files:
        # Only create release and send email if there are actual changes
        logger.info(f"Found {len(matching_files)} relevant changes")
        report = format_changes_report(matching_files, comparison_url, latest)
        update_version_history_as_release(repo, latest.tag_name, previous.tag_name, True, report)
        send_email(report, latest.tag_name, previous.tag_name)
    else:
        logger.info("No relevant changes found - skipping release creation")
if __name__ == "__main__":
    main()

