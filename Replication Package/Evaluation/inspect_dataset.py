import pandas as pd
import os

file_path = 'c:/Personal/issue_analyzing_tool/Replication Package/Evaluation/test_dataset.xlsx'

if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print(f"Total Rows: {len(df)}")
    print(f"Unique Issues: {len(df['Issue URL'].unique())}")
    print(f"Unique Repos: {len(df['Repository'].unique())}")
    print("\nRepos and Issue Counts:")
    print(df['Repository'].value_counts())
else:
    print("Dataset file not found.")
