import pandas as pd

try:
    df = pd.read_excel('evaluation_results_v2.xlsx')
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    # print(df[['Issue URL', 'File Hit', 'Func Hit', 'Line Hit']])

    # Calculate averages
    numeric_cols = ['File Hit', 'File Precision', 'File Recall', 'File F1',
                   'Func Hit', 'Func Precision', 'Func Recall', 'Func F1', 'Duration']

    print("\n--- Average Metrics ---")
    print(df[numeric_cols].mean())

except Exception as e:
    print(f"Error reading results: {e}")
