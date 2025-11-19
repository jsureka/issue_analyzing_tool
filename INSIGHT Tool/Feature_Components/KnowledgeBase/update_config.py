"""
Configuration management for knowledge base updates
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UpdateConfig:
    """Configuration for knowledge base updates"""
    
    # Feature flags
    incremental_update_enabled: bool = True
    auto_clone_repos: bool = True
    log_all_updates: bool = True
    alert_on_failure: bool = False
    
    # Thresholds
    max_files_for_incremental: int = 50
    update_timeout_seconds: int = 300
    max_retries: int = 2
    
    # Paths
    repo_storage_path: str = "Data_Storage/Repositories"
    index_storage_path: str = "indices"
    metrics_storage_path: str = "Data_Storage/update_metrics.json"
    
    # Performance settings
    parallel_file_processing: bool = True
    max_parallel_files: int = 4
    batch_size_incremental: int = 16
    
    # Monitoring settings
    metrics_retention_days: int = 90
    
    # Model settings
    embedding_model: str = "microsoft/unixcoder-base"
    
    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    @classmethod
    def from_env(cls) -> 'UpdateConfig':
        """
        Create configuration from environment variables
        
        Returns:
            UpdateConfig instance
        """
        def get_bool(key: str, default: bool) -> bool:
            """Parse boolean from environment variable"""
            value = os.getenv(key)
            if value is None:
                return default
            return value.lower() in ('true', '1', 'yes', 'on')
        
        def get_int(key: str, default: int) -> int:
            """Parse integer from environment variable"""
            value = os.getenv(key)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {key}: {value}, using default {default}")
                return default
        
        def get_str(key: str, default: str) -> str:
            """Get string from environment variable"""
            return os.getenv(key, default)
        
        config = cls(
            # Feature flags
            incremental_update_enabled=get_bool('INCREMENTAL_UPDATE_ENABLED', True),
            auto_clone_repos=get_bool('AUTO_CLONE_REPOS', True),
            log_all_updates=get_bool('LOG_ALL_UPDATES', True),
            alert_on_failure=get_bool('ALERT_ON_FAILURE', False),
            
            # Thresholds
            max_files_for_incremental=get_int('MAX_FILES_FOR_INCREMENTAL', 50),
            update_timeout_seconds=get_int('UPDATE_TIMEOUT_SECONDS', 300),
            max_retries=get_int('MAX_RETRIES', 2),
            
            # Paths
            repo_storage_path=get_str('REPO_STORAGE_PATH', 'Data_Storage/Repositories'),
            index_storage_path=get_str('INDEX_STORAGE_PATH', 'indices'),
            metrics_storage_path=get_str('METRICS_STORAGE_PATH', 'Data_Storage/update_metrics.json'),
            
            # Performance settings
            parallel_file_processing=get_bool('PARALLEL_FILE_PROCESSING', True),
            max_parallel_files=get_int('MAX_PARALLEL_FILES', 4),
            batch_size_incremental=get_int('BATCH_SIZE_INCREMENTAL', 16),
            
            # Monitoring settings
            metrics_retention_days=get_int('METRICS_RETENTION_DAYS', 90),
            
            # Model settings
            embedding_model=get_str('EMBEDDING_MODEL', 'microsoft/unixcoder-base'),
            
            # Neo4j settings
            neo4j_uri=get_str('NEO4J_URI', 'bolt://localhost:7687'),
            neo4j_user=get_str('NEO4J_USER', 'neo4j'),
            neo4j_password=get_str('NEO4J_PASSWORD', 'password')
        )
        
        logger.info("Loaded configuration from environment variables")
        return config
    
    def validate(self) -> bool:
        """
        Validate configuration values
        
        Returns:
            True if configuration is valid, False otherwise
        """
        valid = True
        
        # Validate thresholds
        if self.max_files_for_incremental <= 0:
            logger.error(f"Invalid max_files_for_incremental: {self.max_files_for_incremental}")
            valid = False
        
        if self.update_timeout_seconds <= 0:
            logger.error(f"Invalid update_timeout_seconds: {self.update_timeout_seconds}")
            valid = False
        
        if self.max_retries < 0:
            logger.error(f"Invalid max_retries: {self.max_retries}")
            valid = False
        
        # Validate performance settings
        if self.max_parallel_files <= 0:
            logger.error(f"Invalid max_parallel_files: {self.max_parallel_files}")
            valid = False
        
        if self.batch_size_incremental <= 0:
            logger.error(f"Invalid batch_size_incremental: {self.batch_size_incremental}")
            valid = False
        
        # Validate retention
        if self.metrics_retention_days <= 0:
            logger.error(f"Invalid metrics_retention_days: {self.metrics_retention_days}")
            valid = False
        
        # Validate paths (basic check)
        if not self.repo_storage_path:
            logger.error("repo_storage_path cannot be empty")
            valid = False
        
        if not self.index_storage_path:
            logger.error("index_storage_path cannot be empty")
            valid = False
        
        if valid:
            logger.info("Configuration validation passed")
        else:
            logger.error("Configuration validation failed")
        
        return valid
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            'incremental_update_enabled': self.incremental_update_enabled,
            'auto_clone_repos': self.auto_clone_repos,
            'log_all_updates': self.log_all_updates,
            'alert_on_failure': self.alert_on_failure,
            'max_files_for_incremental': self.max_files_for_incremental,
            'update_timeout_seconds': self.update_timeout_seconds,
            'max_retries': self.max_retries,
            'repo_storage_path': self.repo_storage_path,
            'index_storage_path': self.index_storage_path,
            'metrics_storage_path': self.metrics_storage_path,
            'parallel_file_processing': self.parallel_file_processing,
            'max_parallel_files': self.max_parallel_files,
            'batch_size_incremental': self.batch_size_incremental,
            'metrics_retention_days': self.metrics_retention_days,
            'embedding_model': self.embedding_model,
            'neo4j_uri': self.neo4j_uri,
            'neo4j_user': self.neo4j_user
            # Note: neo4j_password excluded for security
        }
