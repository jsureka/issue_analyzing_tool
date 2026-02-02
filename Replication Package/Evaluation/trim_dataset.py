import pandas as pd
import os

file_path = 'c:/Personal/issue_analyzing_tool/Replication Package/Evaluation/test_dataset.xlsx'

def trim_dataset():
    if not os.path.exists(file_path):
        print("Dataset file not found.")
        return

    df = pd.read_excel(file_path)
    current_count = len(df)
    target_count = 100
    
    if current_count <= target_count:
        print(f"Current count {current_count} is already <= {target_count}. No trimming needed.")
        return

    to_remove = current_count - target_count
    print(f"Need to remove {to_remove} issues.")

    # Count per repo
    repo_counts = df['Repository'].value_counts()
    print("Current counts:")
    print(repo_counts)

    # Strategy: Remove from the largest repository until we hit the target or it matches the second largest
    # In this specific case, 'databiosphere/toil' has ~46, next is ~14. 
    # Removing 17 from toil leaves 29, still the largest. This is safe.
    
    # We will iterate and remove from the currently largest repo one by one
    
    # Create a list of indices to drop
    drop_indices = []
    
    # We'll work with a mutable copy of counts for logic, but we need to find actual rows
    # Let's just iterate: find largest repo, pick its last issue, mark for removal, repeat.
    
    temp_df = df.copy()
    
    for _ in range(to_remove):
        # recalculate counts
        counts = temp_df['Repository'].value_counts()
        largest_repo = counts.idxmax()
        
        # Find indices for this repo in temp_df
        repo_indices = temp_df[temp_df['Repository'] == largest_repo].index
        
        # Pick the last one (arbitrary, but keeps the 'first' ones which might be better sorted or earlier found)
        idx_to_drop = repo_indices[-1]
        
        drop_indices.append(idx_to_drop)
        temp_df = temp_df.drop(idx_to_drop)
        
    print(f"Removing {len(drop_indices)} rows...")
    df_final = df.drop(drop_indices)
    
    print(f"New total: {len(df_final)}")
    print("New counts:")
    print(df_final['Repository'].value_counts())
    
    df_final.to_excel(file_path, index=False)
    print(f"Saved to {file_path}")

if __name__ == "__main__":
    trim_dataset()
