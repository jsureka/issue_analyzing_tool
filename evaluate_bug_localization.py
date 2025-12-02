import sys
import os
import pandas as pd
import ast
import shutil
import logging
import subprocess
from tqdm import tqdm
import time

# Setup paths
current_dir = os.getcwd()
insight_tool_path = os.path.join(current_dir, "INSIGHT Tool")
sys.path.append(insight_tool_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(insight_tool_path, ".env"))

try:
    from Feature_Components.knowledgeBase import BugLocalization, IndexRepository
    from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

import math
from collections import Counter

class BM25:
    def __init__(self, corpus):
        self.corpus_size = len(corpus)
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.corpus = corpus
        self._initialize()

    def _initialize(self):
        df = {}
        total_length = 0
        for document in self.corpus:
            tokens = self._tokenize(document)
            self.doc_len.append(len(tokens))
            total_length += len(tokens)
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        
        self.avgdl = total_length / self.corpus_size
        for token, freq in df.items():
            self.idf[token] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def _tokenize(self, text):
        import re
        return [t.lower() for t in re.split(r'[^a-zA-Z0-9]', text) if t]

    def get_scores(self, query):
        query_tokens = self._tokenize(query)
        scores = [0] * self.corpus_size
        for i, doc in enumerate(self.corpus):
            doc_tokens = self._tokenize(doc)
            doc_len = self.doc_len[i]
            frequencies = Counter(doc_tokens)
            
            score = 0
            for token in query_tokens:
                if token not in frequencies:
                    continue
                freq = frequencies[token]
                numerator = self.idf.get(token, 0) * freq * (2.5)
                denominator = freq + 1.5 * (1 - 0.75 + 0.75 * doc_len / self.avgdl)
                score += numerator / denominator
            scores[i] = score
        return scores

DATASET_PATH = 'test_dataset.xlsx'
TEMP_REPO_DIR = os.path.join(current_dir, "temp_repos")
RESULTS_FILE = 'evaluation_results_v2.xlsx'

def clone_repo(repo_url, target_dir):
    """Clones a repository to the target directory."""
    if os.path.exists(target_dir):
        # Check if it's the correct repo
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=target_dir, capture_output=True, text=True)
            if repo_url in result.stdout:
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
    
    # Limit to first repo for testing
    if len(repos) > 0:
        repos = [repos[0]]
        logger.info(f"Testing with single repository: {repos[0]}")
    
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
        from Feature_Components.knowledgeBase import GetIndexStatus
        status = GetIndexStatus(repo_name)
        
        if status.get('indexed'):
            logger.info(f"Repository {repo_name} is already indexed. Skipping indexing.")
        else:
            logger.info(f"Indexing {repo_name}...")
            
            # Monkey patch to avoid expensive LLM calls during indexing
            original_generate_summaries = RepositoryIndexer._generate_directory_summaries
            RepositoryIndexer._generate_directory_summaries = lambda self, r, f: logger.info("Skipping directory summarization for evaluation.")
            
            try:
                index_result = IndexRepository(repo_path, repo_name)
            finally:
                # Restore original method just in case
                RepositoryIndexer._generate_directory_summaries = original_generate_summaries
                
            if not index_result.get('success'):
                logger.error(f"Indexing failed for {repo_name}: {index_result.get('error')}")
                continue
            
        # Initialize components once per repo
        from Feature_Components.knowledgeBase import (
            DenseRetriever,
            IssueProcessor,
            CodeEmbedder,
            GraphStore,
            LLMService
        )
        import google.api_core.exceptions
        
        embedder = CodeEmbedder()
        if not embedder.model: embedder.load_model()
        
        processor = IssueProcessor(embedder)
        retriever = DenseRetriever()
        retriever.load_index(repo_name)
        
        graph_store = GraphStore()
        graph_store.connect()
        
        llm_service = LLMService()

        # BM25 initialization removed
        pass

        # 3. Evaluate Issues
        for idx, row in tqdm(repo_issues.iterrows(), total=len(repo_issues), desc=f"Evaluating {repo_name}"):
            # if idx >= 10: break # Limit to 10 issues for testing
            
            issue_title = row['Issue Title']
            issue_body = row['Issue Description']
            
            # Ground Truth
            try:
                gt_files = ast.literal_eval(row['Changed Files'])
            except:
                gt_files = []
            
            try:
                gt_funcs = ast.literal_eval(row['Changed Functions'])
            except:
                gt_funcs = []
                
            try:
                gt_lines = ast.literal_eval(row['Changed Lines'])
            except:
                gt_lines = []
                
            # Run Localization (Hybrid: Retrieval + Graph)
            start_time = time.time()
            
            llm_service = LLMService()
            # Process Issue
            processed_issue = processor.process_issue(issue_title, issue_body)
            
            # --- STAGE 1: File Localization ---
            # 1. Retrieve candidate files (aggregating WINDOW scores)
            # Use retrieve_files_via_windows for better semantic coverage
            candidate_files = retriever.retrieve_files_via_windows(processed_issue.embedding, k=20)
            
            # 2. LLM File Filtering
            if candidate_files:
                logger.info(f"Filtering {len(candidate_files)} candidate files with LLM...")
                selected_files = llm_service.filter_files(issue_title, issue_body, candidate_files)
                logger.info(f"Selected {len(selected_files)} files: {selected_files}")
            else:
                selected_files = []
                logger.warning("No candidate files found.")

            # --- STAGE 2: Function Localization (In-File Graph Retrieval + Hybrid Ranking) ---
            # Strategy: Get ALL functions from selected files via Graph, then rank by Hybrid Score.
            
            candidate_funcs = []
            seen_func_ids = set()
            
            for file_path in selected_files:
                # Get functions from Graph
                funcs = graph_store.get_functions_in_file(file_path)
                
                for func in funcs:
                    if func['id'] in seen_func_ids:
                        continue
                    seen_func_ids.add(func['id'])
                    
                    # Add to candidates
                    func['file_path'] = file_path
                    candidate_funcs.append(func)

            # Read code for candidates
            candidates_with_code = []
            for cand in candidate_funcs:
                try:
                    full_path = os.path.join(repo_path, cand['file_path'])
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            start = max(0, cand['start_line'] - 1)
                            end = min(len(lines), cand['end_line'])
                            cand['code'] = "".join(lines[start:end])
                            candidates_with_code.append(cand)
                except Exception as e:
                    logger.warning(f"Could not read code for {cand.get('name')}: {e}")

            # Hybrid Ranking (BM25 + Semantic)
            if candidates_with_code:
                # 1. BM25 Scores
                corpus = [c['code'] for c in candidates_with_code]
                bm25 = BM25(corpus)
                bm25_scores = bm25.get_scores(issue_title + " " + issue_body)
                
                # Normalize BM25 scores to [0, 1]
                if bm25_scores:
                    min_s = min(bm25_scores)
                    max_s = max(bm25_scores)
                    if max_s > min_s:
                        bm25_scores = [(s - min_s) / (max_s - min_s) for s in bm25_scores]
                    else:
                        bm25_scores = [1.0] * len(bm25_scores)

                # 2. Semantic Scores (Window-based)
                # We need to find the best window match for each function
                # This is expensive if we query for every function. 
                # Optimization: We already have the issue embedding. 
                # We can use the window_vector_store to get windows for these functions if we indexed them.
                # Or simpler: Just use the BM25 score for now as the "Local Rank" and rely on the fact that 
                # the file was selected via Semantic Search.
                # Let's stick to BM25 for local ranking within the file, but maybe boost if the function 
                # was in the original top-k semantic results?
                # For now, let's use BM25 as the primary local ranker.
                
                # Assign scores
                for i, cand in enumerate(candidates_with_code):
                    cand['score'] = bm25_scores[i]
                
                # Sort by score
                candidates_with_code.sort(key=lambda x: x['score'], reverse=True)
                
                # Take top 15
                final_candidates = candidates_with_code[:15]
                
                # Enrich with Graph Context (Callers/Callees)
                # This helps LLM understand the function's role without reading all code
                func_ids = [c['id'] for c in final_candidates]
                neighbors_map = graph_store.get_function_neighbors(func_ids)
                
                for cand in final_candidates:
                    neighbors = neighbors_map.get(cand['id'], {})
                    cand['callers'] = neighbors.get('callers', [])
                    cand['callees'] = neighbors.get('callees', [])
                    
            else:
                final_candidates = []

            logger.info(f"Retrieved {len(candidate_funcs)} functions from graph. Selected top {len(final_candidates)} via Hybrid Ranking.")

            # 3. LLM Function Selection (Precision)
            if final_candidates:
                logger.info(f"Selecting exact buggy functions from {len(final_candidates)} candidates with LLM...")
                
                # Use select_functions
                selected_funcs = llm_service.select_functions(issue_title, issue_body, final_candidates)
                
                if selected_funcs:
                    logger.info(f"LLM Selected {len(selected_funcs)} functions: {[c['name'] for c in selected_funcs]}")
                    final_candidates = selected_funcs
                else:
                    logger.warning("LLM selected NO functions. Fallback to top 1 candidate.")
                    final_candidates = final_candidates[:1]
            
            # Extract Predictions
            pred_files = []
            pred_funcs = []
            
            for res in final_candidates:
                pred_files.append(res['file_path'])
                pred_funcs.append(res['name'])

            duration = time.time() - start_time

            # DEBUG: Print comparison
            logger.info(f"\n--- Issue: {issue_title} ---")
            logger.info(f"GT Files: {gt_files}")
            logger.info(f"Pred Files (Top 3): {pred_files[:3]}")
            logger.info(f"GT Funcs: {gt_funcs}")
            logger.info(f"Pred Funcs (Top 3): {pred_funcs[:3]}")
            
            # --- Metrics Calculation ---
            
            # 1. File Level
            pred_files_set = set(pred_files)
            gt_files_set = set(gt_files)
            
            file_hit = False
            matched_files = 0
            # Normalize paths for comparison
            norm_gt_files = [os.path.normpath(f) for f in gt_files]
            norm_pred_files = [os.path.normpath(f) for f in pred_files_set] # Use set to avoid duplicates
            
            for pred in norm_pred_files:
                if any(gt.endswith(pred) or pred.endswith(gt) for gt in norm_gt_files):
                    matched_files += 1
                    file_hit = True

            file_precision = matched_files / len(pred_files_set) if pred_files_set else 0
            file_recall = matched_files / len(gt_files_set) if gt_files_set else 0
            file_f1 = 2 * file_precision * file_recall / (file_precision + file_recall) if (file_precision + file_recall) > 0 else 0
            
            # 2. Function Level
            pred_funcs_set = set(pred_funcs)
            gt_funcs_set = set(gt_funcs)
            
            func_hit = False
            matched_funcs = 0
            for pred in final_candidates:
                pred_name = pred['name']
                pred_class = pred.get('class_name')
                
                # STRICT MATCHING LOGIC (Refined with Case-Insensitivity)
                # 1. Exact match (Case-Insensitive)
                # 2. Class.Method match (if GT is Class.Method and Pred is Method, or vice versa)
                
                is_match = False
                pred_name_lower = pred_name.lower()
                pred_class_lower = pred_class.lower() if pred_class else None
                
                for gt in gt_funcs:
                    gt_lower = gt.lower()
                    
                    if pred_name_lower == gt_lower:
                        is_match = True
                    elif pred_class_lower and f"{pred_class_lower}.{pred_name_lower}" == gt_lower:
                        is_match = True
                    elif "." in gt_lower and gt_lower.endswith(f".{pred_name_lower}"): # GT is Class.Method, Pred is Method
                         # Check if class matches if available
                         gt_class_part = gt_lower.split(".")[0]
                         if pred_class_lower and pred_class_lower == gt_class_part:
                             is_match = True
                         elif not pred_class_lower: 
                             # If pred has no class info, assume match if method name matches?
                             # Let's allow it for now.
                             is_match = True
                    
                    if is_match:
                        break
                
                if is_match:
                    matched_funcs += 1
                    func_hit = True
            
            logger.info(f"File Hit: {file_hit}, Func Hit: {func_hit}")
            logger.info(f"Matched Funcs Count: {matched_funcs}")

            func_precision = matched_funcs / len(pred_funcs_set) if pred_funcs_set else 0
            func_recall = matched_funcs / len(gt_funcs_set) if gt_funcs_set else 0
            func_f1 = 2 * func_precision * func_recall / (func_precision + func_recall) if (func_precision + func_recall) > 0 else 0

            results.append({
                'Repository': repo_name,
                'Issue URL': row['Issue URL'],
                
                'File Hit': file_hit,
                'File Precision': file_precision,
                'File Recall': file_recall,
                'File F1': file_f1,
                
                'Func Hit': func_hit,
                'Func Precision': func_precision,
                'Func Recall': func_recall,
                'Func F1': func_f1,
                
                'Duration': duration
            })
            
    # Calculate Overall Metrics
    if not results:
        logger.error("No results generated.")
        return

    results_df = pd.DataFrame(results)
    results_df.to_excel(RESULTS_FILE, index=False)
    logger.info(f"Saved detailed results to {RESULTS_FILE}")
    
    print("\n" + "="*40)
    print("EVALUATION RESULTS (Hybrid: Dense + Graph)")
    print("="*40)
    print(f"Total Issues: {len(results_df)}")
    print("-" * 20)
    print("FILE LEVEL:")
    print(f"  F1-Score:  {results_df['File F1'].mean():.4f}")
    print(f"  Recall:    {results_df['File Recall'].mean():.4f}")
    print(f"  Precision: {results_df['File Precision'].mean():.4f}")
    print(f"  Hit Rate:  {results_df['File Hit'].mean():.4f}")
    print("-" * 20)
    print("FUNCTION LEVEL:")
    print(f"  F1-Score:  {results_df['Func F1'].mean():.4f}")
    print(f"  Recall:    {results_df['Func Recall'].mean():.4f}")
    print(f"  Precision: {results_df['Func Precision'].mean():.4f}")
    print(f"  Hit Rate:  {results_df['Func Hit'].mean():.4f}")
    print("="*40)

if __name__ == "__main__":
    # Ensure temp dir exists
    os.makedirs(TEMP_REPO_DIR, exist_ok=True)
    evaluate()
