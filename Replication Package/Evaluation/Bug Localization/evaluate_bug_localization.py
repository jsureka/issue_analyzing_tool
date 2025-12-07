import sys
import os
import pandas as pd
import ast
import shutil
import logging
import subprocess
from tqdm import tqdm
import time
import json

# Setup paths
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))

insight_tool_path = os.path.join(project_root, "INSIGHT Tool")
sys.path.append(insight_tool_path)

# Configure logging
log_file_path = os.path.join(script_dir, 'evaluation_log.txt')
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(insight_tool_path, ".env"))

try:
    from Feature_Components.knowledgeBase import BugLocalization, IndexRepository, GetIndexStatus
    from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer
    from config import Config
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Dataset and output paths
DATASET_PATH = os.path.join(script_dir, '..', 'test_dataset.xlsx')
RESULTS_FILE = os.path.join(script_dir, 'evaluation_results_bug_localization.xlsx')
TEMP_REPO_DIR = os.path.join(project_root, 'temp_repos')

def clone_repo(repo_url, target_dir):
    """Clone a repository if it doesn't exist"""
    if os.path.exists(target_dir):
        # Check if it's a valid git repo
        try:
            result = subprocess.run(['git', '-C', target_dir, 'status'], capture_output=True, check=True)
            logger.info(f"Repository {repo_url} already exists at {target_dir}")
            return True
        except:
            pass
        logger.info(f"Removing existing directory {target_dir}")
        shutil.rmtree(target_dir, ignore_errors=True)
        
    logger.info(f"Cloning {repo_url} to {target_dir}...")
    try:
        subprocess.run(['git', 'clone', repo_url, target_dir], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone {repo_url}: {e}")
        return False

def evaluate():
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found at {DATASET_PATH}")
        return

    df = pd.read_excel(DATASET_PATH)
    logger.info(f"Loaded {len(df)} issues from dataset.")

    results = []
    
    # Group by repository to minimize cloning/indexing
    repos = df['Repository'].unique()
    # Limit to 1 repo for testing as requested
    repos = repos[:1]
    
    for repo_name in repos:
        repo_issues = df[df['Repository'] == repo_name]
        
        repo_url = repo_issues.iloc[0]['Repo Link']
        
        # Prepare local path
        repo_dir_name = repo_name.replace('/', '_')
        repo_path = os.path.join(TEMP_REPO_DIR, repo_dir_name)
        
        # 1. Clone
        if not clone_repo(repo_url, repo_path):
            continue
            
        # 2. Index (Check if already indexed)
        status = GetIndexStatus(repo_name)
        
        if status.get('indexed'):
            logger.info(f"Repository {repo_name} is already indexed. Skipping indexing.")
        else:
            logger.info(f"Indexing {repo_name}...")
            try:
                index_result = IndexRepository(repo_path, repo_name)
            finally:
                if not index_result.get('success'):
                    logger.error(f"Indexing failed for {repo_name}: {index_result.get('error')}")
                    continue
            
        # Initialize BugLocalization
        from Feature_Components.KnowledgeBase.bug_localization import BugLocalization
        bug_localization = BugLocalization(repo_name, repo_path)

        # 3. Evaluate Issues
        for idx, row in tqdm(repo_issues.iterrows(), total=len(repo_issues), desc=f"Evaluating {repo_name}"):
            
            issue_title = row['Issue Title']
            issue_body = row['Issue Description']
            
            # Ground Truth
            try:
                gt_files = ast.literal_eval(row['Changed Files'])
            except:
                gt_files = []
            
            try:
                gt_classes = ast.literal_eval(row['Changed Classes']) if 'Changed Classes' in row else []
            except:
                gt_classes = []
                
            try:
                gt_funcs = ast.literal_eval(row['Changed Functions'])
            except:
                gt_funcs = []
                
            # Run Localization
            start_time = time.time()
            
            try:
                selected_funcs, all_candidates, token_usage = bug_localization.localize(issue_title, issue_body)
            except Exception as e:
                logger.error(f"Error localizing issue {row['Issue URL']}: {e}")
                selected_funcs = []
                all_candidates = []
                token_usage = {}
            
            duration = time.time() - start_time
            
            # Extract Predictions (Top K only)
            pred_files = []
            pred_funcs = []
            if selected_funcs:
                for res in selected_funcs[:Config.LLM_SELECTION_COUNT]:  
                    pred_files.append(res['file_path'])
                    pred_funcs.append(res['name'])
            
            # DEBUG: Print comparison
            logger.info(f"\n--- Issue: {issue_title} ---")
            logger.info(f"GT Files: {gt_files}")
            logger.info(f"Pred Files: {pred_files}")
            logger.info(f"GT Classes: {gt_classes}")
            logger.info(f"GT Funcs: {gt_funcs}")
            logger.info(f"Pred Funcs: {pred_funcs}")
            
            # --- Metrics Calculation (LCA Benchmark) ---
            
            # Helper function for metrics at k
            def calculate_metrics_at_k(predictions, ground_truth, k_values):
                metrics = {}
                norm_gt = {os.path.normpath(f) for f in ground_truth}
                
                for k in k_values:
                    # Top-k predictions
                    top_k_preds = predictions[:k]
                    norm_preds = {os.path.normpath(f) for f in top_k_preds}
                    
                    # True Positives
                    tp = 0
                    for pred in norm_preds:
                        if any(gt.endswith(pred) or pred.endswith(gt) for gt in norm_gt):
                            tp += 1
                    
                    # Hit@k (Is at least one correct?)
                    hit = 1 if tp > 0 else 0
                    
                    # Precision@k
                    precision = tp / k if k > 0 else 0
                    
                    # Recall@k
                    recall = tp / len(norm_gt) if norm_gt else 0

                    # F1@k
                    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                    # All Correct@k
                    all_correct = 1 if (norm_gt and tp == len(norm_gt)) else 0

                    # All Incorrect@k
                    all_incorrect = 1 if tp == 0 else 0
                    
                    metrics[f'Hit@{k}'] = hit
                    metrics[f'Precision@{k}'] = precision
                    metrics[f'Recall@{k}'] = recall
                    metrics[f'F1@{k}'] = f1
                    metrics[f'AllCorrect@{k}'] = all_correct
                    metrics[f'AllIncorrect@{k}'] = all_incorrect
                    metrics[f'AvgTP@{k}'] = tp
                
                return metrics

            # Helper for MAP (Mean Average Precision)
            def calculate_ap(predictions, ground_truth):
                norm_gt = {os.path.normpath(f) for f in ground_truth}
                hits = 0
                sum_precisions = 0
                
                for i, pred in enumerate(predictions):
                    norm_pred = os.path.normpath(pred)
                    if any(gt.endswith(norm_pred) or norm_pred.endswith(gt) for gt in norm_gt):
                        hits += 1
                        precision_at_i = hits / (i + 1)
                        sum_precisions += precision_at_i
                        
                if not norm_gt:
                    return 0.0
                
                return sum_precisions / len(norm_gt)

            # Extract File Paths from Predictions
            # 1. Retrieval Stage (Candidates)
            retrieved_files = []
            seen_files = set()
            for cand in all_candidates:
                fpath = cand['file_path']
                if fpath not in seen_files:
                    retrieved_files.append(fpath)
                    seen_files.add(fpath)
            
            # 2. Final Stage (LLM Selection)
            selected_files = []
            seen_selected = set()
            selected_funcs_names = []
            seen_selected_funcs = set()
            selected_class_names = []
            seen_selected_classes = set()

            for res in selected_funcs:
                # Files
                fpath = res['file_path']
                if fpath not in seen_selected:
                    selected_files.append(fpath)
                    seen_selected.add(fpath)
                
                # Functions
                fname = res['name']
                if fname not in seen_selected_funcs:
                    selected_funcs_names.append(fname)
                    seen_selected_funcs.add(fname)
                
                # Classes (from entity_type or class_name)
                cname = None
                if res.get('entity_type') == 'class':
                    cname = res.get('name')
                elif res.get('class_name'):
                    cname = res.get('class_name')
                
                if cname and cname not in seen_selected_classes:
                    selected_class_names.append(cname)
                    seen_selected_classes.add(cname)

            # Calculate Metrics
            k_values = [1, 5, 10, 20, 30]
            
            # Retriever Metrics (Files)
            retriever_metrics = calculate_metrics_at_k(retrieved_files, gt_files, k_values)
            retriever_map = calculate_ap(retrieved_files, gt_files)
            
            # LLM Metrics (Files) - k=[1, 3, 5, 10]
            llm_metrics = calculate_metrics_at_k(selected_files, gt_files, [1, 3, 5, 10])
            llm_map = calculate_ap(selected_files, gt_files)

            # LLM Metrics (Classes) - k=[1, 3, 5, 10]
            llm_class_metrics = calculate_metrics_at_k(selected_class_names, gt_classes, [1, 3, 5, 10])
            llm_class_map = calculate_ap(selected_class_names, gt_classes)

            # LLM Metrics (Functions) - k=[1, 3, 5, 10]
            llm_func_metrics = calculate_metrics_at_k(selected_funcs_names, gt_funcs, [1, 3, 5, 10])
            llm_func_map = calculate_ap(selected_funcs_names, gt_funcs)
            
            # Combine Results
            result_row = {
                'Repository': repo_name,
                'Issue URL': row['Issue URL'],
                'Model': bug_localization.llm_service.model_name,
                
                # Retriever Metrics
                'Retriever MAP': retriever_map,
                **{f'Retriever {k}': v for k, v in retriever_metrics.items()},
                
                # LLM Metrics (Files)
                'LLM File MAP': llm_map,
                **{f'LLM File {k}': v for k, v in llm_metrics.items()},

                # LLM Metrics (Classes)
                'LLM Class MAP': llm_class_map,
                **{f'LLM Class {k}': v for k, v in llm_class_metrics.items()},

                # LLM Metrics (Functions)
                'LLM Func MAP': llm_func_map,
                **{f'LLM Func {k}': v for k, v in llm_func_metrics.items()},
                
                'Input Tokens': token_usage.get('input_tokens', token_usage.get('prompt_tokens', 0)) if token_usage else 0,
                'Output Tokens': token_usage.get('output_tokens', token_usage.get('completion_tokens', 0)) if token_usage else 0,
                'Total Tokens': token_usage.get('total_tokens', 0) if token_usage else 0,
                'Duration': duration
            }
            results.append(result_row)
            
    # Calculate Overall Metrics
    if not results:
        logger.error("No results generated.")
        return

    results_df = pd.DataFrame(results)
    try:
        results_df.to_excel(RESULTS_FILE, index=False)
        logger.info(f"Saved detailed results to {RESULTS_FILE}")
    except PermissionError:
        logger.error(f"Permission denied when writing to {RESULTS_FILE}. The file might be open.")
        backup_file = RESULTS_FILE.replace('.xlsx', f'_backup_{int(time.time())}.xlsx')
        logger.info(f"Attempting to save to backup file: {backup_file}")
        try:
            results_df.to_excel(backup_file, index=False)
            logger.info(f"Results successfully saved to backup file: {backup_file}")
        except Exception as e:
            logger.error(f"Failed to save backup file: {e}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
    
    print("\n" + "="*60)
    print(f"LCA BENCHMARK RESULTS (Model: {results[0]['Model']})")
    print("="*60)
    print(f"Total Issues: {len(results_df)}")
    print("-" * 30)
    print("RETRIEVER METRICS (Search Stage - Files):")
    print(f"MAP:         {results_df['Retriever MAP'].mean():.4f}")
    print(f"Hit@1:       {results_df['Retriever Hit@1'].mean():.4f}")
    print(f"Hit@5:       {results_df['Retriever Hit@5'].mean():.4f}")
    print(f"Hit@10:      {results_df['Retriever Hit@10'].mean():.4f}")
    print(f"Recall@10:   {results_df['Retriever Recall@10'].mean():.4f}")
    print(f"Recall@20:   {results_df['Retriever Recall@20'].mean():.4f}")
    print("-" * 30)
    print("LLM METRICS (Final Selection - Files):")
    print(f"MAP:         {results_df['LLM File MAP'].mean():.4f}")
    print(f"Hit@1:       {results_df['LLM File Hit@1'].mean():.4f}")
    print(f"Hit@3:       {results_df['LLM File Hit@3'].mean():.4f}")
    print(f"Hit@5:       {results_df['LLM File Hit@5'].mean():.4f}")
    print(f"Hit@10:      {results_df['LLM File Hit@10'].mean():.4f}")
    print(f"Recall@3:    {results_df['LLM File Recall@3'].mean():.4f}")
    print(f"Recall@5:    {results_df['LLM File Recall@5'].mean():.4f}")
    print(f"Recall@10:   {results_df['LLM File Recall@10'].mean():.4f}")
    print(f"Precision@1: {results_df['LLM File Precision@1'].mean():.4f}")
    print(f"Precision@3: {results_df['LLM File Precision@3'].mean():.4f}")
    print(f"Precision@10: {results_df['LLM File Precision@10'].mean():.4f}")
    print(f"F1@3:        {results_df['LLM File F1@3'].mean():.4f}")
    print(f"F1@5:        {results_df['LLM File F1@5'].mean():.4f}")
    print(f"F1@10:       {results_df['LLM File F1@10'].mean():.4f}")
    print(f"All Correct@3:    {results_df['LLM File AllCorrect@3'].mean():.4f}")
    print(f"All Incorrect@3:  {results_df['LLM File AllIncorrect@3'].mean():.4f}")
    print(f"Avg Buggy Files Detected@3: {results_df['LLM File AvgTP@3'].mean():.2f}")
    print("-" * 30)
    print("LLM METRICS (Final Selection - Classes):")
    print(f"MAP:         {results_df['LLM Class MAP'].mean():.4f}")
    print(f"Hit@1:       {results_df['LLM Class Hit@1'].mean():.4f}")
    print(f"Hit@3:       {results_df['LLM Class Hit@3'].mean():.4f}")
    print(f"Hit@5:       {results_df['LLM Class Hit@5'].mean():.4f}")
    print(f"Hit@10:      {results_df['LLM Class Hit@10'].mean():.4f}")
    print(f"Recall@3:    {results_df['LLM Class Recall@3'].mean():.4f}")
    print(f"Recall@5:    {results_df['LLM Class Recall@5'].mean():.4f}")
    print(f"Recall@10:   {results_df['LLM Class Recall@10'].mean():.4f}")
    print(f"Precision@1: {results_df['LLM Class Precision@1'].mean():.4f}")
    print(f"Precision@3: {results_df['LLM Class Precision@3'].mean():.4f}")
    print(f"Precision@10: {results_df['LLM Class Precision@10'].mean():.4f}")
    print(f"F1@3:        {results_df['LLM Class F1@3'].mean():.4f}")
    print(f"F1@5:        {results_df['LLM Class F1@5'].mean():.4f}")
    print(f"F1@10:       {results_df['LLM Class F1@10'].mean():.4f}")
    print(f"All Correct@3:    {results_df['LLM Class AllCorrect@3'].mean():.4f}")
    print(f"All Incorrect@3:  {results_df['LLM Class AllIncorrect@3'].mean():.4f}")
    print("-" * 30)
    print("LLM METRICS (Final Selection - Functions):")
    print(f"MAP:         {results_df['LLM Func MAP'].mean():.4f}")
    print(f"Hit@1:       {results_df['LLM Func Hit@1'].mean():.4f}")
    print(f"Hit@3:       {results_df['LLM Func Hit@3'].mean():.4f}")
    print(f"Hit@5:       {results_df['LLM Func Hit@5'].mean():.4f}")
    print(f"Hit@10:      {results_df['LLM Func Hit@10'].mean():.4f}")
    print(f"Recall@3:    {results_df['LLM Func Recall@3'].mean():.4f}")
    print(f"Recall@5:    {results_df['LLM Func Recall@5'].mean():.4f}")
    print(f"Recall@10:   {results_df['LLM Func Recall@10'].mean():.4f}")
    print(f"Precision@1: {results_df['LLM Func Precision@1'].mean():.4f}")
    print(f"Precision@3: {results_df['LLM Func Precision@3'].mean():.4f}")
    print(f"Precision@10: {results_df['LLM Func Precision@10'].mean():.4f}")
    print(f"F1@3:        {results_df['LLM Func F1@3'].mean():.4f}")
    print(f"F1@5:        {results_df['LLM Func F1@5'].mean():.4f}")
    print(f"F1@10:       {results_df['LLM Func F1@10'].mean():.4f}")
    print(f"All Correct@3:    {results_df['LLM Func AllCorrect@3'].mean():.4f}")
    print(f"All Incorrect@3:  {results_df['LLM Func AllIncorrect@3'].mean():.4f}")
    print("-" * 30)
    print("TOKEN USAGE:")
    print(f"Avg Total Tokens:    {results_df['Total Tokens'].mean():.0f}")
    print(f"Total All Tokens:    {results_df['Total Tokens'].sum():.0f}")
    print("="*60)

if __name__ == "__main__":
    # Ensure temp dir exists
    os.makedirs(TEMP_REPO_DIR, exist_ok=True)
    evaluate()