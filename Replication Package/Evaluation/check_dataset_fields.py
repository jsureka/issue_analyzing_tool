from datasets import load_dataset

print("Loading Java dataset...")
ds = load_dataset('JetBrains-Research/lca-bug-localization', 'java', split='test', trust_remote_code=True)

print("\nAll available fields:")
for k in sorted(ds[0].keys()):
    print(f"  - {k}")

print("\n\nSample data from first item:")
sample = ds[0]
for k in sorted(sample.keys()):
    val = sample[k]
    if isinstance(val, str) and len(val) > 100:
        print(f"{k}: {val[:100]}...")
    else:
        print(f"{k}: {val}")
