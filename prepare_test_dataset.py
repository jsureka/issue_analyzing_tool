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
    valid_repos = {k: v for k, v in repo_issues.items() if len(v) >= min_issues}
    print(f"Found {len(valid_repos)} repositories with >= {min_issues} issues.")
    
    # Sort by number of issues (descending) and take top N
    sorted_repos = sorted(valid_repos.items(), key=lambda x: len(x[1]), reverse=True)[:num_repos]
    
    extracted_data = []
    
    for repo_name, issues in sorted_repos:
        print(f"  Extracting from {repo_name} ({len(issues)} issues)...")
        # Take up to 10 issues (or all if close to 10)
        # The requirement says "having 10 issues atleast", so we can take 10.
        selected_issues = issues[:10] 
        
        for issue in selected_issues:
            diff_text = issue.get('diff', '')
            changed_funcs, changed_lines = parse_diff(diff_text)
            
            # Construct row
            row = {
                'Language': lang_code,
                'Repository': repo_name,
                'Repo Link': f"https://github.com/{repo_name}",
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
