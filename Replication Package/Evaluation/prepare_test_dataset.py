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

    # Group by repository
    repo_issues = {}
    
    print(f"Total examples in {lang_code}: {len(all_ds)}")
    
    for item in all_ds:
        # Try to get repo info from html_url or issue_url
        url = item.get('html_url') or item.get('issue_url')
        if not url:
            continue
            
        owner, name = get_repo_info(url)
        if not owner or not name:
            continue
            
        repo_full_name = f"{owner}/{name}"
        if repo_full_name not in repo_issues:
            repo_issues[repo_full_name] = []
        
        repo_issues[repo_full_name].append(item)
    
    # Filter repos with enough issues
    valid_repos_list = [k for k, v in repo_issues.items() if len(v) >= min_issues]
    print(f"Found {len(valid_repos_list)} repositories with >= {min_issues} issues.")
    
    # Fetch details for valid repos to sort by size
    repo_details_map = {}
    print("Fetching repository details (size, file count)...")
    
    # Limit checking to avoid massive wait times if there are hundreds of repos
    # But user asked for smallest, so we should try to check as many as reasonable.
    # Let's check up to 50 candidates.
    candidates = valid_repos_list[:50] 
    if len(valid_repos_list) > 50:
        print(f"Warning: Checking only first 50 repositories out of {len(valid_repos_list)} to avoid rate limits.")
    
    for repo_full_name in candidates:
        owner, name = repo_full_name.split('/')
        details = get_repo_details(owner, name)
        if details:
            repo_details_map[repo_full_name] = details
            print(f"  {repo_full_name}: Size={details['size']}KB, Files={details['file_count']}")
        time.sleep(0.5) # Slight delay to be nice to API
        
    # Sort by size (ascending)
    # Filter out repos where we couldn't get details
    sorted_repos_by_size = sorted(
        [r for r in repo_details_map.keys()],
        key=lambda r: repo_details_map[r]['size']
    )
    
    # Take top N smallest
    selected_repo_names = sorted_repos_by_size[:num_repos]
    
    extracted_data = []
    
    for repo_name in selected_repo_names:
        issues = repo_issues[repo_name]
        details = repo_details_map[repo_name]
        print(f"  Extracting from {repo_name} (Size: {details['size']}KB, Files: {details['file_count']})...")
        
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
                'Repo Size (KB)': details['size'],
                'Total Files': details['file_count'],
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
    all_data = []
    
    # Python
    py_data = process_language('py')
    all_data.extend(py_data)
    
    # Java
    java_data = process_language('java')
    all_data.extend(java_data)
    
    if not all_data:
        print("No data extracted!")
        return

    df = pd.DataFrame(all_data)
    output_file = 'test_dataset.xlsx'
    
    print(f"Saving {len(df)} rows to {output_file}...")
    try:
        df.to_excel(output_file, index=False)
        print("Done!")
    except ImportError:
        print("openpyxl not installed. Saving as CSV instead.")
        df.to_csv('test_dataset.csv', index=False)
        print("Saved to test_dataset.csv")

if __name__ == "__main__":
    main()
