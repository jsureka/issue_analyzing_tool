"""
Update metrics tracking and monitoring
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UpdateMetrics:
    """Track and monitor knowledge base update metrics"""
    
    def __init__(self, storage_path: str = "Data_Storage/update_metrics.json"):
        """
        Initialize update metrics tracker
        
        Args:
            storage_path: Path to metrics storage file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.metrics: List[Dict[str, Any]] = []
        self._load_metrics()
        
        logger.info(f"UpdateMetrics initialized with storage: {storage_path}")
    
    def _load_metrics(self):
        """Load existing metrics from file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.metrics = data.get('updates', [])
                logger.info(f"Loaded {len(self.metrics)} metric entries")
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")
                self.metrics = []
        else:
            self.metrics = []
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            data = {
                'total_updates': len(self.metrics),
                'last_updated': datetime.utcnow().isoformat(),
                'updates': self.metrics
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.metrics)} metric entries")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def log_update(self, update_info: Dict[str, Any]):
        """
        Log an update event
        
        Args:
            update_info: Dictionary with update information
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in update_info:
                update_info['timestamp'] = datetime.utcnow().isoformat()
            
            # Add to metrics list
            self.metrics.append(update_info)
            
            # Save to file
            self._save_metrics()
            
            logger.info(
                f"Logged update for {update_info.get('repo_name', 'unknown')}: "
                f"{update_info.get('type', 'unknown')} "
                f"({'success' if update_info.get('success') else 'failed'})"
            )
            
        except Exception as e:
            logger.error(f"Failed to log update: {e}")
    
    def get_recent_updates(self, repo_name: Optional[str] = None, 
                          limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent updates
        
        Args:
            repo_name: Filter by repository name (optional)
            limit: Maximum number of updates to return
            
        Returns:
            List of update dictionaries
        """
        try:
            # Filter by repo if specified
            if repo_name:
                filtered = [m for m in self.metrics if m.get('repo_name') == repo_name]
            else:
                filtered = self.metrics
            
            # Sort by timestamp descending
            sorted_metrics = sorted(
                filtered,
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            # Return last N
            return sorted_metrics[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent updates: {e}")
            return []
    
    def get_statistics(self, repo_name: Optional[str] = None,
                      days: int = 30) -> Dict[str, Any]:
        """
        Get update statistics
        
        Args:
            repo_name: Filter by repository name (optional)
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            # Filter metrics
            filtered = [
                m for m in self.metrics
                if m.get('timestamp', '') >= cutoff_str
            ]
            
            if repo_name:
                filtered = [m for m in filtered if m.get('repo_name') == repo_name]
            
            if not filtered:
                return {
                    'total_updates': 0,
                    'successful_updates': 0,
                    'failed_updates': 0,
                    'success_rate': 0.0,
                    'average_update_time': 0.0,
                    'average_files_changed': 0.0,
                    'update_types': {}
                }
            
            # Calculate statistics
            total = len(filtered)
            successful = sum(1 for m in filtered if m.get('success', False))
            failed = total - successful
            
            # Average update time
            times = [m.get('total_time_seconds', 0) for m in filtered if 'total_time_seconds' in m]
            avg_time = sum(times) / len(times) if times else 0.0
            
            # Average files changed
            files = [m.get('files_changed', 0) for m in filtered if 'files_changed' in m]
            avg_files = sum(files) / len(files) if files else 0.0
            
            # Update types
            update_types = {}
            for m in filtered:
                update_type = m.get('type', 'unknown')
                update_types[update_type] = update_types.get(update_type, 0) + 1
            
            return {
                'total_updates': total,
                'successful_updates': successful,
                'failed_updates': failed,
                'success_rate': (successful / total * 100) if total > 0 else 0.0,
                'average_update_time': avg_time,
                'average_files_changed': avg_files,
                'update_types': update_types,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {}
    
    def cleanup_old_metrics(self, days: int = 90):
        """
        Remove metrics older than specified days
        
        Args:
            days: Number of days to keep
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            original_count = len(self.metrics)
            self.metrics = [
                m for m in self.metrics
                if m.get('timestamp', '') >= cutoff_str
            ]
            
            removed = original_count - len(self.metrics)
            if removed > 0:
                self._save_metrics()
                logger.info(f"Cleaned up {removed} old metric entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    def get_repository_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary statistics for all repositories
        
        Returns:
            Dictionary mapping repo names to their statistics
        """
        try:
            # Get unique repository names
            repo_names = set(m.get('repo_name') for m in self.metrics if m.get('repo_name'))
            
            summary = {}
            for repo_name in repo_names:
                summary[repo_name] = self.get_statistics(repo_name=repo_name, days=30)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get repository summary: {e}")
            return {}
