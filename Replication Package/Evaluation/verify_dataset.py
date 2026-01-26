import pandas as pd
import sys

def verify_dataset(file_path):
    print(f"Verifying {file_path}...")
    try:
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    print(f"Total rows: {len(df)}")
    
    # Check uniqueness
    duplicates = df[df.duplicated(subset=['Issue URL'], keep=False)]
    if not duplicates.empty:
        print(f"CRITICAL: Found {len(duplicates)} duplicate Issue URLs!")
    else:
        print("PASS: No duplicate Issue URLs found.")

    # Check Counts per Repo
    repo_counts = df['Repository'].value_counts()
    print("\nCounts per Repository:")
    print(repo_counts)
    
    # Check max limit
    over_limit = repo_counts[repo_counts > 5]
    if not over_limit.empty:
        print(f"\nWARNING: The following repositories have MORE than 5 issues (Expected <= 5):")
        print(over_limit)
    else:
        print("\nPASS: All repositories have 5 or fewer issues.")
        
    # Check min limit (warning)
    low_count = repo_counts[repo_counts < 4]
    if not low_count.empty:
        print(f"\nWARNING: Some repositories have fewer than 4 issues:")
        print(low_count)

    print(f"\nTotal Repositories: {len(repo_counts)}")
    # We expect 9 existing + 4 new = 13 repos
    if len(repo_counts) >= 13:
        print("PASS: Repository count matches target (>=13).")
    else:
         print(f"WARNING: Expected at least 13 repositories, found {len(repo_counts)}.")
         
    if len(df) >= 55: # Approximate check for 60
         print(f"PASS: Total issues ({len(df)}) meets target (~60).")
    else:
         print(f"WARNING: Total issues ({len(df)}) below target (~60).")

if __name__ == "__main__":
    verify_dataset('test_dataset.xlsx')
