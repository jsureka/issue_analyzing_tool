"""
Auto Labeler - Automatically applies GitHub labels based on confidence levels
"""

import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AutoLabeler:
    """Automatically labels GitHub issues based on bug localization confidence"""
    
    # Label definitions
    CONFIDENCE_LABELS = {
        'high': {
            'name': 'bug-localization:high-confidence',
            'color': '0e8a16',  # Green
            'description': 'Bug localization has high confidence (>90% accuracy)'
        },
        'medium': {
            'name': 'bug-localization:medium-confidence',
            'color': 'fbca04',  # Yellow
            'description': 'Bug localization has medium confidence (~70% accuracy)'
        },
        'low': {
            'name': 'bug-localization:low-confidence',
            'color': 'd93f0b',  # Red
            'description': 'Bug localization has low confidence (<50% accuracy)'
        }
    }
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        """
        Initialize auto labeler
        
        Args:
            github_token: GitHub API token
            repo_owner: Repository owner
            repo_name: Repository name
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
        logger.info(f"AutoLabeler initialized for {repo_owner}/{repo_name}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication"""
        return {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def ensure_labels_exist(self) -> bool:
        """
        Create confidence labels if they don't exist in the repository
        
        Returns:
            True if successful
        """
        try:
            for confidence, label_info in self.CONFIDENCE_LABELS.items():
                # Check if label exists
                url = f"{self.base_url}/labels/{label_info['name']}"
                response = requests.get(url, headers=self._get_headers())
                
                if response.status_code == 404:
                    # Label doesn't exist, create it
                    create_url = f"{self.base_url}/labels"
                    payload = {
                        'name': label_info['name'],
                        'color': label_info['color'],
                        'description': label_info['description']
                    }
                    
                    create_response = requests.post(
                        create_url,
                        headers=self._get_headers(),
                        json=payload
                    )
                    
                    if create_response.status_code == 201:
                        logger.info(f"Created label: {label_info['name']}")
                    else:
                        logger.warning(f"Failed to create label {label_info['name']}: {create_response.text}")
                elif response.status_code == 200:
                    logger.debug(f"Label already exists: {label_info['name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure labels exist: {e}")
            return False
    
    def apply_confidence_label(self, issue_number: int, confidence: str,
                              max_retries: int = 3) -> bool:
        """
        Apply confidence label to issue, removing old confidence labels
        
        Args:
            issue_number: GitHub issue number
            confidence: Confidence level ("high", "medium", "low")
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if successful
        """
        if confidence not in self.CONFIDENCE_LABELS:
            logger.error(f"Invalid confidence level: {confidence}")
            return False
        
        try:
            # First, remove any existing confidence labels
            self._remove_confidence_labels(issue_number)
            
            # Apply new label with retries
            label_name = self.CONFIDENCE_LABELS[confidence]['name']
            
            for attempt in range(max_retries):
                try:
                    url = f"{self.base_url}/issues/{issue_number}/labels"
                    payload = {'labels': [label_name]}
                    
                    response = requests.post(
                        url,
                        headers=self._get_headers(),
                        json=payload
                    )
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"Applied label '{label_name}' to issue #{issue_number}")
                        return True
                    elif response.status_code == 404:
                        logger.error(f"Issue #{issue_number} not found")
                        return False
                    else:
                        logger.warning(f"Failed to apply label (attempt {attempt + 1}): {response.text}")
                        
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(2 ** attempt)  # Exponential backoff
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)
            
            logger.error(f"Failed to apply label after {max_retries} attempts")
            return False
            
        except Exception as e:
            logger.error(f"Failed to apply confidence label: {e}")
            return False
    
    def _remove_confidence_labels(self, issue_number: int) -> bool:
        """
        Remove all confidence labels from an issue
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            True if successful
        """
        try:
            # Get current labels
            url = f"{self.base_url}/issues/{issue_number}/labels"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code != 200:
                logger.warning(f"Failed to get current labels: {response.text}")
                return False
            
            current_labels = response.json()
            
            # Remove confidence labels
            for label in current_labels:
                label_name = label.get('name', '')
                if label_name.startswith('bug-localization:') and 'confidence' in label_name:
                    delete_url = f"{self.base_url}/issues/{issue_number}/labels/{label_name}"
                    delete_response = requests.delete(delete_url, headers=self._get_headers())
                    
                    if delete_response.status_code in [200, 204]:
                        logger.debug(f"Removed label '{label_name}' from issue #{issue_number}")
                    else:
                        logger.warning(f"Failed to remove label '{label_name}': {delete_response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove confidence labels: {e}")
            return False
    
    def get_issue_labels(self, issue_number: int) -> List[str]:
        """
        Get all labels for an issue
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            List of label names
        """
        try:
            url = f"{self.base_url}/issues/{issue_number}/labels"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                labels = response.json()
                return [label.get('name', '') for label in labels]
            else:
                logger.warning(f"Failed to get labels: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get issue labels: {e}")
            return []
