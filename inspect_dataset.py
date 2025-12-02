from datasets import load_dataset

def inspect_dataset():
    print("Loading dataset...")
    ds = load_dataset("JetBrains-Research/lca-bug-localization", "py", split="test", trust_remote_code=True)
    
    print("\nDataset Columns:")
    print(ds.column_names)
    
    print("\nFirst Example:")
    example = ds[0]
    for key, value in example.items():
        print(f"{key}: {str(value)[:200]}...") # Print first 200 chars

if __name__ == "__main__":
    inspect_dataset()
