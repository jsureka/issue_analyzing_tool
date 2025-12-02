from datasets import load_dataset

def inspect_dataset():
    print("Loading dataset...")
    ds = load_dataset("JetBrains-Research/lca-bug-localization", "py", split="test", trust_remote_code=True)
    
    print("\nDataset Columns:", ds.column_names)
    
    print("\nFirst Example Keys:", ds[0].keys())
    
    # Check for specific fields
    example = ds[0]
    print(f"Repo Name: {example.get('repo_name', 'N/A')}")
    print(f"Repo Owner: {example.get('repo_owner', 'N/A')}")
    print(f"Issue URL: {example.get('issue_url', 'N/A')}")
    print(f"HTML URL: {example.get('html_url', 'N/A')}")
    print(f"Diff URL: {example.get('diff_url', 'N/A')}")
    
    # Print a bit of the diff to see format
    print(f"Diff Start: {str(example.get('diff', ''))[:100]}")

if __name__ == "__main__":
    inspect_dataset()
