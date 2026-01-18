from datasets import load_dataset
import json

def inspect_dataset():
    print("Loading one example from JetBrains-Research/lca-bug-localization (py)...")
    try:
        ds = load_dataset("JetBrains-Research/lca-bug-localization", "py", split="test", streaming=True, trust_remote_code=True)
        for item in ds:
            print("\n--- AVAILABLE KEYS ---")
            keys =  list(item.keys())
            keys.sort()
            for k in keys:
                print(f"- {k}")
            
            print("\n--- RELEVANT VALUES ---")
            for k in keys:
                if any(x in k.lower() for x in ['sha', 'commit', 'hash', 'url', 'diff', 'id']):
                    val = item[k]
                    if isinstance(val, str) and len(val) > 100:
                        val = val[:100] + "..."
                    print(f"{k}: {val}")
            
            # Explicitly check for commit hashes in specific likely fields if not obvious
            print("\n--- COMMIT CANDIDATES ---")
            # Usually 'fix_commit_sha' or similar
            
            break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_dataset()
