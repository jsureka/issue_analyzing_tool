import pandas as pd
from datasets import load_dataset
import re
from collections import Counter
import os

def parse_diff(diff_text):
    """
    Parses a git diff to extract changed functions and lines.
    This is a heuristic parser.
    """
    changed_functions = set()
    changed_lines = []
    
    # Regex to find function definitions in diff context or added lines
    # This is simplified and might need adjustment based on actual diff format
    # Looking for '@@ ... @@ def func' or similar
    
    lines = diff_text.split('\n')
    current_file = None
    
    # Regex for hunk header: @@ -1,5 +1,5 @@ ...
    hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@\s*(.*)')
    
    current_line_num = 0
    
    for line in lines:
        if line.startswith('diff --git'):
            continue
        
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            current_line_num = int(hunk_match.group(1))
            context = hunk_match.group(2)
            # Try to extract function name from context
            # Python: def foo(...) or class Foo
            # Java: public void foo(...)
            if context:
                # Simple extraction of the last word before ( or just the whole context
                # Cleaning up context to get function name
                func_match = re.search(r'(?:def|class|void|int|String|public|private|protected)\s+([a-zA-Z0-9_]+)', context)
                if func_match:
                    changed_functions.add(func_match.group(1))
                else:
                    # Fallback: just use the context text if it looks like code
                    if '(' in context:
                         changed_functions.add(context.strip())
            continue

        if line.startswith('+') and not line.startswith('+++'):
            changed_lines.append(current_line_num)
            current_line_num += 1
        elif line.startswith(' ') or (line.startswith('-') and not line.startswith('---')):
            if not line.startswith('-'):
                current_line_num += 1
                
    return list(changed_functions), changed_lines

def get_repo_info(url):
    """Extracts owner and repo name from a GitHub URL."""
    if not url:
        return None, None
    # Example: https://github.com/owner/repo/issues/123
    # or https://github.com/owner/repo
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

import requests
import time

def get_github_token():
    """Retrieves the GitHub token from the environment variable."""
    return os.environ.get("GITHUB_TOKEN")

def get_repo_details(owner, name):
    """
    Fetches repository details (size, file count) from GitHub API.
    Returns a dictionary with 'size' (in KB) and 'file_count'.
    """
    token = get_github_token()
    headers = {"Authorization": f"token {token}"} if token else {}
    
    # Get repo metadata for size
    api_url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            size_kb = data.get('size', 0)
            default_branch = data.get('default_branch', 'main')
            
            # Get file count using Tree API (recursive)
            # Note: Tree API has limits, but for small repos it should be fine.
            tree_url = f"https://api.github.com/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1"
            tree_response = requests.get(tree_url, headers=headers)
            file_count = 0
            if tree_response.status_code == 200:
                tree_data = tree_response.json()
                # Count items of type 'blob' (files)
                file_count = len([item for item in tree_data.get('tree', []) if item.get('type') == 'blob'])
            else:
                print(f"    Warning: Could not fetch tree for {owner}/{name}: {tree_response.status_code}")
            
            return {'size': size_kb, 'file_count': file_count}
        elif response.status_code == 403:
            print(f"    Rate limit exceeded or forbidden for {owner}/{name}")
            return None
        else:
            print(f"    Could not fetch metadata for {owner}/{name}: {response.status_code}")
            return None
    except Exception as e:
        print(f"    Error fetching details for {owner}/{name}: {e}")
        return None

def process_language(lang_code, num_repos=3, min_issues=10):
    print(f"Processing language: {lang_code}...")
    splits = ['test', 'train', 'validation']
    all_ds = []
    for split in splits:
        try:
            print(f"Loading {split} split for {lang_code}...")
            ds = load_dataset("JetBrains-Research/lca-bug-localization", lang_code, split=split, trust_remote_code=True)
            all_ds.extend(list(ds))
        except Exception as e:
            print(f"Could not load {split} split for {lang_code}: {e}")
            
    if not all_ds:
        print(f"No data found for {lang_code}")
        return []

    # Group by repository and collect repo metadata from dataset
    repo_issues = {}
    repo_metadata = {}
    
    print(f"Total examples in {lang_code}: {len(all_ds)}")
    
    for item in all_ds:
        # Get repo info from dataset fields
        owner = item.get('repo_owner')
        name = item.get('repo_name')
        
        if not owner or not name:
            # Fallback: Try to get from URL
            url = item.get('html_url') or item.get('issue_url')
            if url:
                owner, name = get_repo_info(url)
            if not owner or not name:
                continue
            
        repo_full_name = f"{owner}/{name}"
        if repo_full_name not in repo_issues:
            repo_issues[repo_full_name] = []
            # Store repo metadata from dataset (no API calls needed!)
            repo_metadata[repo_full_name] = {
                'file_count': item.get('repo_files_without_tests_count', 0),
                'lines_count': item.get('repo_lines_count', 0),
                'stars': item.get('repo_stars', 0),
                'language': item.get('repo_language', lang_code)
            }
        
        repo_issues[repo_full_name].append(item)
    
    # Filter repos with enough issues
    valid_repos_list = [k for k, v in repo_issues.items() if len(v) >= min_issues]
    print(f"Found {len(valid_repos_list)} repositories with >= {min_issues} issues.")
    
    # Sort by file count (ascending) - no API calls needed!
    sorted_repos_by_size = sorted(
        valid_repos_list,
        key=lambda r: repo_metadata[r]['file_count']
    )
    
    print(f"\nSmallest repositories by file count:")
    for repo in sorted_repos_by_size[:num_repos]:
        meta = repo_metadata[repo]
        print(f"  {repo}: Files={meta['file_count']}, Lines={meta['lines_count']}, Stars={meta['stars']}")
    
    # Take top N smallest
    selected_repo_names = sorted_repos_by_size[:num_repos]
    
    extracted_data = []
    
    for repo_name in selected_repo_names:
        issues = repo_issues[repo_name]
        meta = repo_metadata[repo_name]
        print(f"\n  Extracting from {repo_name} (Files: {meta['file_count']}, Lines: {meta['lines_count']})...")
        
        # Take up to 10 issues
        selected_issues = issues[:10] 
        
        for issue in selected_issues:
            diff_text = issue.get('diff', '')
            changed_funcs, changed_lines = parse_diff(diff_text)
            
            # Construct row
            row = {
                'Language': lang_code,
                'Repository': repo_name,
                'Repo Link': f"https://github.com/{repo_name}",
                'Repo Size (KB)': meta.get('lines_count', 0) // 50,  # Rough estimate: ~50 lines per KB
                'Total Files': meta['file_count'],
                'Issue Title': issue.get('issue_title'),
                'Issue Description': issue.get('issue_body'),
                'Issue URL': issue.get('html_url') or issue.get('issue_url'),
                'Changed Files': str(issue.get('changed_files')),
                'Changed Functions': str(changed_funcs),
                'Changed Lines': str(changed_lines)[:1000], # Truncate if too long
                'Diff URL': issue.get('diff_url')
            }
            extracted_data.append(row)
            
    return extracted_data

def main():
    output_file = 'test_dataset.xlsx'
    csv_fallback = 'test_dataset.csv'
    
    # Load existing data if file exists
    existing_data = []
    existing_issue_urls = set()
    
    if os.path.exists(output_file):
        print(f"Found existing dataset: {output_file}")
        try:
            existing_df = pd.read_excel(output_file)
            existing_data = existing_df.to_dict('records')
            existing_issue_urls = set(existing_df['Issue URL'].dropna().values)
            print(f"Loaded {len(existing_data)} existing rows")
            
            # Create backup
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'test_dataset_backup_{timestamp}.xlsx'
            existing_df.to_excel(backup_file, index=False)
            print(f"Created backup: {backup_file}")
        except Exception as e:
            print(f"Could not load existing Excel file: {e}")
            # Try CSV fallback
            if os.path.exists(csv_fallback):
                print(f"Trying to load from CSV: {csv_fallback}")
                existing_df = pd.read_csv(csv_fallback)
                existing_data = existing_df.to_dict('records')
                existing_issue_urls = set(existing_df['Issue URL'].dropna().values)
                print(f"Loaded {len(existing_data)} existing rows from CSV")
    
    all_data = existing_data.copy()
    
    # Python
    py_data = process_language('py')
    new_py_count = 0
    for row in py_data:
        if row['Issue URL'] not in existing_issue_urls:
            all_data.append(row)
            existing_issue_urls.add(row['Issue URL'])
            new_py_count += 1
    print(f"Added {new_py_count} new Python issues (skipped {len(py_data) - new_py_count} duplicates)")
    
    # Java
    java_data = process_language('java')
    new_java_count = 0
    for row in java_data:
        if row['Issue URL'] not in existing_issue_urls:
            all_data.append(row)
            existing_issue_urls.add(row['Issue URL'])
            new_java_count += 1
    print(f"Added {new_java_count} new Java issues (skipped {len(java_data) - new_java_count} duplicates)")
    
    if not all_data:
        print("No data to save!")
        return

    df = pd.DataFrame(all_data)
    
    print(f"\nSaving {len(df)} total rows ({len(existing_data)} existing + {new_py_count + new_java_count} new) to {output_file}...")
    try:
        df.to_excel(output_file, index=False)
        print("Done!")
    except ImportError:
        print("openpyxl not installed. Saving as CSV instead.")
        df.to_csv(csv_fallback, index=False)
        print(f"Saved to {csv_fallback}")

if __name__ == "__main__":
    main()
