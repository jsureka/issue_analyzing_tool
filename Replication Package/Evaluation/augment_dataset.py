import pandas as pd
from datasets import load_dataset
import re
import os
import requests

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
        class_match = re.search(r'class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            classes_set.add(class_match.group(1))
            return
        
        func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', context)
        if func_match:
            functions_set.add(func_match.group(1))
    
    elif language == 'java':
        class_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:abstract)?\s*class\s+([A-Z][a-zA-Z0-9_]*)', context)
        if class_match:
            classes_set.add(class_match.group(1))
            return
        
        interface_match = re.search(r'(?:public|private|protected)?\s*interface\s+([A-Z][a-zA-Z0-9_]*)', context)
        if interface_match:
            classes_set.add(interface_match.group(1))
            return
        
        # Exclude Java keywords that might be matched
        method_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:\w+(?:<[^>]+>)?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', context)
        if method_match:
            method_name = method_match.group(1)
            if method_name not in ['class', 'interface', 'enum', 'extends', 'implements', 'throws']:
                functions_set.add(method_name)

def parse_diff(diff_text):
    changed_files = set()
    changed_classes = set()
    changed_functions = set()
    changed_lines = []
    
    lines = diff_text.split('\n')
    current_file = None
    current_language = None
    
    hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@\s*(.*)')
    current_line_num = 0
    
    for line in lines:
        if line.startswith('diff --git'):
            match = re.search(r'b/(.+)$', line)
            if match:
                current_file = match.group(1)
                changed_files.add(current_file)
                current_language = detect_language(current_file)
            continue
        
        if line.startswith('+++') and line.startswith('+++ b/'):
            file_path = line[6:].strip()
            if file_path:
                changed_files.add(file_path)
                current_file = file_path
                current_language = detect_language(current_file)
            continue
        
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            current_line_num = int(hunk_match.group(1))
            context = hunk_match.group(2)
            extract_entities(context, current_language, changed_classes, changed_functions)
            continue

        if line.startswith('+') and not line.startswith('+++'):
            changed_lines.append(current_line_num)
            current_line_num += 1
            extract_entities(line[1:], current_language, changed_classes, changed_functions)
            
        elif line.startswith(' '):
            current_line_num += 1
            extract_entities(line[1:], current_language, changed_classes, changed_functions)
            
        elif line.startswith('-') and not line.startswith('---'):
            pass
                
    return list(changed_files), list(changed_classes), list(changed_functions), changed_lines

def get_repo_info(url):
    if not url:
        return None, None
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def get_github_token():
    return os.environ.get("GITHUB_TOKEN")

def get_repo_details(owner, name):
    token = get_github_token()
    headers = {"Authorization": f"token {token}"} if token else {}
    api_url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            size_kb = data.get('size', 0)
            default_branch = data.get('default_branch', 'main')
            tree_url = f"https://api.github.com/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1"
            tree_response = requests.get(tree_url, headers=headers)
            file_count = 0
            if tree_response.status_code == 200:
                tree_data = tree_response.json()
                file_count = len([item for item in tree_data.get('tree', []) if item.get('type') == 'blob'])
            return {'size': size_kb, 'file_count': file_count}
    except Exception as e:
        pass
    return None

def process_repos(lang_code, target_repos):
    print(f"Processing language: {lang_code} for repos: {target_repos}")
    splits = ['test', 'train', 'dev']
    all_ds = []
    for split in splits:
        try:
            print(f"Loading {split} split for {lang_code}...")
            # Using trust_remote_code=True as in original script
            ds = load_dataset("JetBrains-Research/lca-bug-localization", lang_code, split=split, trust_remote_code=True)
            all_ds.extend(list(ds))
        except Exception as e:
            print(f"Could not load {split} split for {lang_code}: {e}")
            
    if not all_ds:
        return []

    repo_issues = {}
    repo_metadata = {}
    
    # Pre-filter dataset to only relevant repos
    target_repos_lower = {r.lower() for r in target_repos}
    
    for item in all_ds:
        owner = item.get('repo_owner')
        name = item.get('repo_name')
        
        if not owner or not name:
            url = item.get('html_url') or item.get('issue_url')
            if url:
                owner, name = get_repo_info(url)
            if not owner or not name:
                continue
            
        repo_full_name = f"{owner}/{name}"
        if repo_full_name.lower() in target_repos_lower:
            # Normalize key
            key = repo_full_name 
            # But we want to match the exact casing if possible, or just use what we found
            if key not in repo_issues:
                repo_issues[key] = []
                repo_metadata[key] = {
                    'file_count': item.get('repo_files_without_tests_count', 0),
                    'lines_count': item.get('repo_lines_count', 0),
                    'stars': item.get('repo_stars', 0),
                    'language': item.get('repo_language', lang_code)
                }
            repo_issues[key].append(item)
    
    extracted_data = []
    
    for repo_name in repo_issues:
        issues = repo_issues[repo_name]
        meta = repo_metadata[repo_name]
        print(f"  Found {len(issues)} issues for {repo_name}")
        
        # Take up to 10 issues
        selected_issues = issues[:10]
        
        for issue in selected_issues:
            diff_text = issue.get('diff', '')
            changed_files, changed_classes, changed_funcs, changed_lines = parse_diff(diff_text)
            
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

def find_new_java_repos(num_repos=3, min_issues=8):
    print(f"Searching for new Java repositories...")
    splits = ['test', 'train', 'dev']
    all_ds = []
    for split in splits:
        try:
            print(f"Loading {split} split for java...")
            ds = load_dataset("JetBrains-Research/lca-bug-localization", "java", split=split, trust_remote_code=True)
            all_ds.extend(list(ds))
        except Exception as e:
            print(f"Could not load {split} split for java: {e}")
            
    if not all_ds:
        return []

    repo_issues = {}
    repo_metadata = {}
    
    for item in all_ds:
        owner = item.get('repo_owner')
        name = item.get('repo_name')
        
        if not owner or not name:
            url = item.get('html_url') or item.get('issue_url')
            if url:
                owner, name = get_repo_info(url)
            if not owner or not name:
                continue
            
        repo_full_name = f"{owner}/{name}"
        if repo_full_name not in repo_issues:
            repo_issues[repo_full_name] = []
            repo_metadata[repo_full_name] = {
                'file_count': item.get('repo_files_without_tests_count', 0),
                'lines_count': item.get('repo_lines_count', 0),
                'stars': item.get('repo_stars', 0),
                'language': 'java'
            }
        repo_issues[repo_full_name].append(item)
    
    # Filter candidates
    valid_repos = []
    for r, issues in repo_issues.items():
        if len(issues) >= min_issues:
            fc = repo_metadata[r]['file_count']
            # Target small repos: 20 to 500 files
            if 20 <= fc <= 500:
                valid_repos.append(r)
    
    print(f"Found {len(valid_repos)} valid Java candidate repos (>= {min_issues} issues, 20-500 files).")
    
    # Sort by file count ascending
    valid_repos.sort(key=lambda r: repo_metadata[r]['file_count'])
    
    selected_repos = valid_repos[:num_repos]
    print(f"Selected Java repos: {selected_repos}")
    
    return process_repos('java', selected_repos)

def main():
    existing_file = 'test_dataset.xlsx'
    
    if os.path.exists(existing_file):
        print("Reading existing dataset...")
        df_existing = pd.read_excel(existing_file)
        current_repos = df_existing['Repository'].unique().tolist()
    else:
        df_existing = pd.DataFrame()
        current_repos = []
        
    print(f"Current Repositories: {current_repos}")
    
    all_new_data = []
    
    # 1. Update existing repos (which we know are Python currently)
    # Actually, let's keep the existing data as is, and ONLY append new Java stuff?
    # No, the previous run updated the existing repos to have up to 10 issues.
    # So we should just LOAD the valid rows from the file.
    
    # But if we run this script again, we want to make sure we don't duplicate or lose data.
    # The user wants "check if there are java repositories here or not".
    
    has_java = any(lang == 'java' for lang in df_existing.get('Language', []).unique())
    
    if not has_java:
        print("No Java repositories found. Adding 3 small Java repositories...")
        java_data = find_new_java_repos(num_repos=3, min_issues=8)
        if java_data:
            # Create DF 
            df_java = pd.DataFrame(java_data)
            # Concat
            df_final = pd.concat([df_existing, df_java], ignore_index=True)
            
            # Save
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'test_dataset_backup_{timestamp}.xlsx'
            try:
                os.rename(existing_file, backup_file)
                print(f"Backed up existing dataset to {backup_file}")
            except Exception as e:
                print(f"Warning backup failed: {e}")
                
            print(f"Saving {len(df_final)} total rows to {existing_file}...")
            df_final.to_excel(existing_file, index=False)
            print("Done adding Java repos.")
        else:
            print("Could not find suitable Java repos.")
    else:
        print("Java repositories already exist. Skipping addition.")

if __name__ == "__main__":
    main()
