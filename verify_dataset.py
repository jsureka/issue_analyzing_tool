import pandas as pd

def verify_dataset():
    try:
        df = pd.read_excel('test_dataset.xlsx')
        print(f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns.")
        print("Columns:", df.columns.tolist())
        
        print("\nFirst row:")
        print(df.iloc[0])
        
        # Check for empty fields
        print("\nMissing values:")
        print(df.isnull().sum())
        
        # Check unique repos
        print("\nRepositories included:")
        print(df.groupby('Language')['Repository'].unique())
        
    except Exception as e:
        print(f"Error verifying dataset: {e}")

if __name__ == "__main__":
    verify_dataset()
