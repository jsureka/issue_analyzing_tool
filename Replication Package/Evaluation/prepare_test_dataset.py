import pandas as pd
from datasets import load_dataset
import re
from collections import Counter
import os
import requests
import time

def detect_language(file_path):
    """Detect programming language from file extension"""
    if file_path.endswith('.py'):
        return 'python'
    elif file_path.endswith('.java'):
        return 'java'
    return 'unknown'

def extract_entities(context, language, classes_set, functions_set):
    """Extract class and function names from diff hunk context"""
    if not context:
        return
    
    if language == 'python':
        # Extract class names: class ClassName or class ClassName(Base)
        class_match = re.search(r'class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            classes_set.add(class_match.group(1))
            return  # If we found a class, don't look for functions in the same line
        
        # Extract function/method names: def function_name
        func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', context)
        if func_match:
            functions_set.add(func_match.group(1))
    
    elif language == 'java':
        # Extract class names: class ClassName, public class ClassName, etc.
        class_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:abstract)?\s*class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            classes_set.add(class_match.group(1))
            return  # If we found a class, don't look for methods
        
        # Extract interface names
        interface_match = re.search(r'(?:public|private|protected)?\s*interface\s+([A-Z][a-zA-Z0-9_]*)', context)
        if interface_match:
            classes_set.add(interface_match.group(1))
            return
        
        # Extract method names: public void methodName( or private String methodName(
        # More comprehensive regex for Java methods
        method_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:\w+(?:<[^>]+>)?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', context)
        if method_match:
            method_name = method_match.group(1)
            # Exclude Java keywords that might be matched
            if method_name not in ['class', 'interface', 'enum', 'extends', 'implements', 'throws']:
                functions_set.add(method_name)

def parse_diff(diff_text):
    """
    Parses a git diff to extract changed files, classes, and functions separately.
    Returns four lists: files, classes, functions, changed_lines
    """
    changed_files = set()
    changed_classes = set()
    changed_functions = set()
    changed_lines = []
    
    lines = diff_text.split('\n')
    current_file = None
    current_language = None
    
    # Regex for hunk header: @@ -1,5 +1,5 @@ ...
    hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@\s*(.*)')
    
    current_line_num = 0
    
    for line in lines:
        # Extract file path from diff header
        if line.startswith('diff --git'):
            # Format: diff --git a/path/to/file.py b/path/to/file.py
            match = re.search(r'b/(.+)$', line)
            if match:
                current_file = match.group(1)
                changed_files.add(current_file)
                current_language = detect_language(current_file)
            continue
        
        # Also handle +++ b/file format
        if line.startswith('+++') and line.startswith('+++ b/'):
            file_path = line[6:].strip()
            if file_path:
                changed_files.add(file_path)
                current_file = file_path
                current_language = detect_language(current_file)
            continue
        
        # Extract from hunk headers
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            current_line_num = int(hunk_match.group(1))
            context = hunk_match.group(2)
            extract_entities(context, current_language, changed_classes, changed_functions)
            continue

        # Track changed line numbers and scan for entities in the body
        if line.startswith('+') and not line.startswith('+++'):
            changed_lines.append(current_line_num)
            current_line_num += 1
            # Check for new definitions in added lines
            extract_entities(line[1:], current_language, changed_classes, changed_functions)
            
        elif line.startswith(' '):
            current_line_num += 1
            # Check for context definitions (e.g. knowing we are inside a function)
            # This is heuristic but helps if header missed it.
            extract_entities(line[1:], current_language, changed_classes, changed_functions)
            
        elif line.startswith('-') and not line.startswith('---'):
            # Deleted lines
            # logic doesn't change current_line_num for deleted lines in target file
            pass
                
    return list(changed_files), list(changed_classes), list(changed_functions), changed_lines

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

def process_language(lang_code, target_repos=None, num_new_repos=0, max_issues=5):
    """
    Process language split.
    target_repos: set of existing repos to preserve
    num_new_repos: number of additional NEW repos to find
    max_issues: max unique issues per repo
    """
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
        
        # If we have target repos, and we are NOT looking for new ones, we could filter here.
        # But since we might be looking for new ones, we need to collect initial data.
        # However, to save memory, if target_repos IS set and num_new_repos is 0, we can filter.
        if target_repos is not None and num_new_repos == 0:
             if repo_full_name not in target_repos:
                 continue

        if repo_full_name not in repo_issues:
            repo_issues[repo_full_name] = []
            repo_metadata[repo_full_name] = {
                'file_count': item.get('repo_files_without_tests_count', 0),
                'lines_count': item.get('repo_lines_count', 0),
                'stars': item.get('repo_stars', 0),
                'language': item.get('repo_language', lang_code)
            }
        
        repo_issues[repo_full_name].append(item)
    
    selected_repo_names = []
    
    # 1. Select Existing Target Repos
    if target_repos is not None:
        found_targets = [r for r in repo_issues.keys() if r in target_repos]
        print(f"  Found {len(found_targets)} existing target repositories in {lang_code} split.")
        selected_repo_names.extend(found_targets)
        
    # 2. Select NEW Repos if requested
    if num_new_repos > 0:
        print(f"  Searching for {num_new_repos} new {lang_code} repositories...")
        candidates = []
        for r, issues in repo_issues.items():
            # Skip if already in targets
            if target_repos is not None and r in target_repos:
                continue
            
            # Check constraints
            fc = repo_metadata[r]['file_count']
            if not (50 < fc < 200):
                continue
                
            # Check unique issues count (at least max_issues to be useful)
            unique_urls = set()
            for i in issues:
                u = i.get('html_url') or i.get('issue_url')
                if u: unique_urls.add(u)
            
            if len(unique_urls) >= max_issues:
                candidates.append(r)
        
        print(f"  Found {len(candidates)} candidate new repositories.")
        
        # Sort by file count (smallest first)
        sorted_candidates = sorted(
            candidates,
            key=lambda r: repo_metadata[r]['file_count']
        )
        
        new_selections = sorted_candidates[:num_new_repos]
        selected_repo_names.extend(new_selections)
        print(f"  Selected new repositories: {new_selections}")

    extracted_data = []
    
    for repo_name in selected_repo_names:
        issues = repo_issues[repo_name]
        meta = repo_metadata[repo_name]
        
        # Deduplicate issues by URL
        unique_issues = {}
        for issue in issues:
            url = issue.get('html_url') or issue.get('issue_url')
            if url and url not in unique_issues:
                unique_issues[url] = issue
        
        final_issues = list(unique_issues.values())
        
        print(f"\n  Extracting from {repo_name} (Files: {meta['file_count']}). Found {len(final_issues)} unique issues.")
        
        # Limit to max_issues
        selected_issues_batch = final_issues[:max_issues]
        
        for issue in selected_issues_batch:
            diff_text = issue.get('diff', '')
            changed_files, changed_classes, changed_funcs, changed_lines = parse_diff(diff_text)
            
            # Construct row
            row = {
                'Language': lang_code,
                'Repository': repo_name,
                'Repo Link': f"https://github.com/{repo_name}",
                'Repo Size (KB)': meta.get('lines_count', 0) // 50,
                'Total Files': meta['file_count'],
                'Issue Title': issue.get('issue_title'),
                'Issue Description': issue.get('issue_body'),
                'Issue URL': issue.get('html_url') or issue.get('issue_url'),
                'Changed Files': str(changed_files),
                'Changed Classes': str(changed_classes),
                'Changed Functions': str(changed_funcs),
                'Changed Lines': str(changed_lines)[:1000],
                'Diff URL': issue.get('diff_url'),
                'Base SHA': issue.get('base_sha'),
                'Head SHA': issue.get('head_sha')
            }
            extracted_data.append(row)
            
    return extracted_data

def get_target_repos(file_path):
    """
    Reads the existing dataset file and extracts the list of unique repositories.
    """
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} does not exist. Cannot preserve repos.")
        return None
        
    try:
        # Check extension
        if file_path.endswith('.xlsx'):
             df = pd.read_excel(file_path)
        else:
             df = pd.read_csv(file_path)
        
        if 'Repository' not in df.columns:
             print("Repository column not found.")
             return None

        repos = set(df['Repository'].unique())
        print(f"Loaded {len(repos)} target repositories from {file_path}")
        return repos
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def main():
    output_file = 'test_dataset.xlsx'
    
    target_repos = get_target_repos(output_file)
    
    # Backup
    if os.path.exists(output_file):
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'test_dataset_backup_{timestamp}.xlsx'
        try:
           os.rename(output_file, backup_file)
           print(f"Backed up existing dataset to {backup_file} before recreation.")
        except Exception as e:
           print(f"Warning: Could not backup existing file: {e}")

    all_data = []
    
    # Process Python: Preserve existing, 2 NEW, max 5 issues
    py_data = process_language('py', target_repos=target_repos, num_new_repos=2, max_issues=5)
    all_data.extend(py_data)
    
    # Process Java: Preserve existing, 2 NEW, max 5 issues
    java_data = process_language('java', target_repos=target_repos, num_new_repos=2, max_issues=5)
    all_data.extend(java_data)
    
    if not all_data:
        print("No data to save!")
        return

    df = pd.DataFrame(all_data)
    
    # Deduplicate global rows
    df.drop_duplicates(subset=['Issue URL'], inplace=True)
    
    print(f"\nSaving {len(df)} total rows to {output_file}...")
    try:
        df.to_excel(output_file, index=False)
        print("Done!")
    except ImportError:
        print("openpyxl not installed. Saving as CSV instead.")
        df.to_csv('test_dataset.csv', index=False)
        print("Saved to test_dataset.csv")

if __name__ == "__main__":
    main()
