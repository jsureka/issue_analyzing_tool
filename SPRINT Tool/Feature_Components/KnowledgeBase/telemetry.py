"""
Telemetry Logger - Tracks performance metrics and system health
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """Logs and tracks performance metrics for the Knowledge Base System"""
    
    def __init__(self, log_path: str = "telemetry_logs"):
        """
        Initialize telemetry logger
        
        Args:
            log_path: Directory path for telemetry log files
        """
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory metrics for quick access
        self._metrics = {
            'retrieval': [],
            'indexing': [],
            'errors': []
        }
        self._lock = threading.Lock()
        
        # Configure JSON log file
        self.log_file = self.log_path / f"telemetry_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        logger.info(f"TelemetryLogger initialized, logging to {self.log_file}")
    
    def log_retrieval(self, issue_id: str, latency_ms: float, top_k: int, 
                     confidence: str, repo_name: str = "", success: bool = True) -> None:
        """
        Log retrieval metrics
        
        Args:
            issue_id: GitHub issue ID or number
            latency_ms: Retrieval latency in milliseconds
            top_k: Number of results returned
            confidence: Confidence level (high/medium/low)
            repo_name: Repository name
            success: Whether retrieval succeeded
        """
        try:
            metric = {
                'type': 'retrieval',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'issue_id': issue_id,
                'latency_ms': latency_ms,
                'top_k': top_k,
                'confidence': confidence,
                'repo_name': repo_name,
                'success': success
            }
            
            # Write to log file
            self._write_log(metric)
            
            # Store in memory
            with self._lock:
                self._metrics['retrieval'].append(metric)
                # Keep only last 1000 entries in memory
                if len(self._metrics['retrieval']) > 1000:
                    self._metrics['retrieval'] = self._metrics['retrieval'][-1000:]
            
            logger.debug(f"Logged retrieval: issue={issue_id}, latency={latency_ms}ms, confidence={confidence}")
            
        except Exception as e:
            logger.error(f"Failed to log retrieval metrics: {e}")
    
    def log_indexing(self, repo_name: str, files_indexed: int, 
                    duration_seconds: float, functions_count: int = 0,
                    success: bool = True, error_msg: str = "") -> None:
        """
        Log indexing metrics
        
        Args:
            repo_name: Repository name
            files_indexed: Number of files indexed
            duration_seconds: Indexing duration in seconds
            functions_count: Number of functions indexed
            success: Whether indexing succeeded
            error_msg: Error message if failed
        """
        try:
            metric = {
                'type': 'indexing',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'repo_name': repo_name,
                'files_indexed': files_indexed,
                'functions_count': functions_count,
                'duration_seconds': duration_seconds,
                'success': success,
                'error_msg': error_msg
            }
            
            # Write to log file
            self._write_log(metric)
            
            # Store in memory
            with self._lock:
                self._metrics['indexing'].append(metric)
                if len(self._metrics['indexing']) > 1000:
                    self._metrics['indexing'] = self._metrics['indexing'][-1000:]
            
            logger.debug(f"Logged indexing: repo={repo_name}, files={files_indexed}, duration={duration_seconds}s")
            
        except Exception as e:
            logger.error(f"Failed to log indexing metrics: {e}")

    
    def log_error(self, error_type: str, error_msg: str, context: Dict[str, Any] = None) -> None:
        """
        Log error with context
        
        Args:
            error_type: Type of error (e.g., 'retrieval_failed', 'indexing_failed')
            error_msg: Error message
            context: Additional context (issue_id, repo_name, stack_trace, etc.)
        """
        try:
            metric = {
                'type': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'error_type': error_type,
                'error_msg': error_msg,
                'context': context or {}
            }
            
            # Write to log file
            self._write_log(metric)
            
            # Store in memory
            with self._lock:
                self._metrics['errors'].append(metric)
                if len(self._metrics['errors']) > 1000:
                    self._metrics['errors'] = self._metrics['errors'][-1000:]
            
            logger.error(f"Logged error: type={error_type}, msg={error_msg}")
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def _write_log(self, metric: Dict[str, Any]) -> None:
        """
        Write metric to JSON log file
        
        Args:
            metric: Metric dictionary to log
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    def get_statistics(self, time_range: str = "24h") -> Dict[str, Any]:
        """
        Compute aggregate statistics over time range
        
        Args:
            time_range: Time range for statistics (e.g., "1h", "24h", "7d")
            
        Returns:
            Dictionary with aggregate statistics
        """
        try:
            # Parse time range
            cutoff_time = self._parse_time_range(time_range)
            
            with self._lock:
                # Filter metrics by time range
                recent_retrievals = [
                    m for m in self._metrics['retrieval']
                    if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) >= cutoff_time
                ]
                recent_indexing = [
                    m for m in self._metrics['indexing']
                    if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) >= cutoff_time
                ]
                recent_errors = [
                    m for m in self._metrics['errors']
                    if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) >= cutoff_time
                ]
            
            # Compute retrieval statistics
            retrieval_stats = self._compute_retrieval_stats(recent_retrievals)
            
            # Compute indexing statistics
            indexing_stats = self._compute_indexing_stats(recent_indexing)
            
            # Compute error statistics
            error_stats = self._compute_error_stats(recent_errors)
            
            return {
                'time_range': time_range,
                'period_start': cutoff_time.isoformat() + 'Z',
                'period_end': datetime.utcnow().isoformat() + 'Z',
                'retrieval': retrieval_stats,
                'indexing': indexing_stats,
                'errors': error_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to compute statistics: {e}")
            return {}
    
    def _parse_time_range(self, time_range: str) -> datetime:
        """
        Parse time range string to datetime
        
        Args:
            time_range: Time range string (e.g., "1h", "24h", "7d")
            
        Returns:
            Cutoff datetime (timezone-aware)
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            return now - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            return now - timedelta(days=days)
        elif time_range.endswith('m'):
            minutes = int(time_range[:-1])
            return now - timedelta(minutes=minutes)
        else:
            # Default to 24 hours
            return now - timedelta(hours=24)
    
    def _compute_retrieval_stats(self, retrievals: list) -> Dict[str, Any]:
        """Compute retrieval statistics"""
        if not retrievals:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_latency_ms': 0.0,
                'median_latency_ms': 0.0,
                'p95_latency_ms': 0.0,
                'confidence_distribution': {}
            }
        
        successful = [r for r in retrievals if r.get('success', True)]
        latencies = [r['latency_ms'] for r in successful if 'latency_ms' in r]
        latencies.sort()
        
        # Confidence distribution
        confidence_dist = defaultdict(int)
        for r in successful:
            conf = r.get('confidence', 'unknown')
            confidence_dist[conf] += 1
        
        return {
            'total_requests': len(retrievals),
            'successful_requests': len(successful),
            'success_rate': len(successful) / len(retrievals) if retrievals else 0.0,
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0.0,
            'median_latency_ms': latencies[len(latencies)//2] if latencies else 0.0,
            'p95_latency_ms': latencies[int(len(latencies)*0.95)] if latencies else 0.0,
            'confidence_distribution': dict(confidence_dist)
        }
    
    def _compute_indexing_stats(self, indexing: list) -> Dict[str, Any]:
        """Compute indexing statistics"""
        if not indexing:
            return {
                'total_operations': 0,
                'success_rate': 0.0,
                'total_files_indexed': 0,
                'total_functions_indexed': 0,
                'avg_duration_seconds': 0.0
            }
        
        successful = [i for i in indexing if i.get('success', True)]
        durations = [i['duration_seconds'] for i in successful if 'duration_seconds' in i]
        
        return {
            'total_operations': len(indexing),
            'successful_operations': len(successful),
            'success_rate': len(successful) / len(indexing) if indexing else 0.0,
            'total_files_indexed': sum(i.get('files_indexed', 0) for i in successful),
            'total_functions_indexed': sum(i.get('functions_count', 0) for i in successful),
            'avg_duration_seconds': sum(durations) / len(durations) if durations else 0.0
        }
    
    def _compute_error_stats(self, errors: list) -> Dict[str, Any]:
        """Compute error statistics"""
        if not errors:
            return {
                'total_errors': 0,
                'error_types': {}
            }
        
        # Error type distribution
        error_types = defaultdict(int)
        for e in errors:
            error_type = e.get('error_type', 'unknown')
            error_types[error_type] += 1
        
        return {
            'total_errors': len(errors),
            'error_types': dict(error_types)
        }


# Global telemetry logger instance
_telemetry_logger = None


def get_telemetry_logger(log_path: str = "telemetry_logs") -> TelemetryLogger:
    """
    Get or create global telemetry logger instance
    
    Args:
        log_path: Directory path for telemetry log files
        
    Returns:
        TelemetryLogger instance
    """
    global _telemetry_logger
    if _telemetry_logger is None:
        _telemetry_logger = TelemetryLogger(log_path)
    return _telemetry_logger
