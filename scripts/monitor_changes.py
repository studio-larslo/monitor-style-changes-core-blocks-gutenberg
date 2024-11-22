"""
Monitor changes between releases with test mode support
"""
from github import Github
import os
import re
import logging
from packaging import version

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_specific_releases(repo, base_tag=None, head_tag=None):
    """Get specific releases for testing"""
    logger.info(f"Fetching specific releases: {base_tag} → {head_tag}")
    if base_tag and head_tag:
        try:
            base_release = repo.get_release(base_tag)
            head_release = repo.get_release(head_tag)
            return [head_release, base_release]
        except Exception as e:
            logger.error(f"Error fetching specific releases: {e}")
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
    """Compare two releases and return all changed files"""
    logger.info(f"Comparing releases: {base_tag} → {head_tag}")
    
    comparison = repo.compare(base_tag, head_tag)
    changed_files = []
    
    for file in comparison.files:
        changed_files.append({
            'filename': file.filename,
            'status': file.status,
            'changes': file.changes
        })
    
    return changed_files

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
    
    if added:
        report += "## Added Files\n"
        for file in added:
            report += f"- `{file['filename']}`\n"
        report += "\n"
    
    if modified:
        report += "## Modified Files\n"
        for file in modified:
            report += f"- `{file['filename']}` ({file['changes']} changes)\n"
        report += "\n"
    
    if removed:
        report += "## Removed Files\n"
        for file in removed:
            report += f"- `{file['filename']}`\n"
        report += "\n"
    
    report += f"\n[View full comparison on GitHub]({comparison_url})"
    return report

def main():
    # Get configuration from environment
    github_token = os.environ['GITHUB_TOKEN']
    target_repo = os.environ.get('TARGET_REPO', 'WordPress/gutenberg')
    test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    base_tag = os.environ.get('BASE_TAG')
    head_tag = os.environ.get('HEAD_TAG')
    
    logger.info(f"Starting release monitoring for: {target_repo}")
    logger.info(f"Test mode: {test_mode}")
    
    g = Github(github_token)
    repo = g.get_repo(target_repo)
    
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
    
    # Check for relevant changes
    matching_files = check_file_changes(repo, previous.tag_name, latest.tag_name)
    
    if matching_files:
        logger.info(f"Found {len(matching_files)} relevant changes")
        report = format_changes_report(
            matching_files,
            f"https://github.com/{target_repo}/compare/{previous.tag_name}...{latest.tag_name}",
            latest
        )
        
        # Save report to file for GitHub Actions
        with open('changes_report.md', 'w') as f:
            f.write(report)
        
        # Set environment variable for GitHub Actions
        print("::set-env name=CHANGES_FOUND::true")
        
        if test_mode:
            print("\n" + "="*80 + "\n")
            print(report)
            print("\n" + "="*80 + "\n")
    else:
        logger.info("No relevant changes found")

if __name__ == "__main__":
    main()

