"""
Confidence Calibrator - Maps similarity scores to calibrated confidence levels
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result from validation dataset"""
    issue_id: str
    predicted_functions: List[str]
    true_function: str
    top_score: float
    in_top_3: bool


class ConfidenceCalibrator:
    """Calibrates similarity scores to confidence levels"""
    
    def __init__(self, calibration_config_path: str = "calibration_config.json"):
        """
        Initialize confidence calibrator
        
        Args:
            calibration_config_path: Path to calibration configuration file
        """
        self.config_path = Path(calibration_config_path)
        self.thresholds = self._load_default_thresholds()
        
        # Try to load existing calibration
        if self.config_path.exists():
            self.load_calibration_config()
        
        logger.info(f"ConfidenceCalibrator initialized with config: {calibration_config_path}")
    
    def _load_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """
        Load default confidence thresholds
        
        Returns:
            Dictionary with default thresholds
        """
        return {
            'high': {
                'min_score': 0.75,
                'precision_at_3': 0.90
            },
            'medium': {
                'min_score': 0.55,
                'max_score': 0.75,
                'precision_at_3': 0.70
            },
            'low': {
                'max_score': 0.55,
                'precision_at_3': 0.40
            }
        }
    
    def load_calibration_config(self) -> bool:
        """
        Load calibration configuration from file
        
        Returns:
            True if successful
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.thresholds = config.get('thresholds', self.thresholds)
            
            logger.info(f"Loaded calibration config from {self.config_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load calibration config: {e}")
            return False
    
    def save_calibration_config(self, validation_date: str = None, 
                               validation_size: int = 0,
                               model_version: str = "unixcoder-base") -> bool:
        """
        Save calibration configuration to file
        
        Args:
            validation_date: Date of validation
            validation_size: Number of validation samples
            model_version: Model version used
            
        Returns:
            True if successful
        """
        try:
            from datetime import datetime
            
            config = {
                'model_version': model_version,
                'validation_date': validation_date or datetime.utcnow().isoformat(),
                'validation_size': validation_size,
                'thresholds': self.thresholds
            }
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved calibration config to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save calibration config: {e}")
            return False
    
    def calibrate_score(self, similarity_score: float) -> Tuple[str, float]:
        """
        Map similarity score to confidence level and calibrated probability
        
        Args:
            similarity_score: Raw similarity score (0-1)
            
        Returns:
            Tuple of (confidence_level, calibrated_probability)
        """
        # Determine confidence level based on thresholds
        if similarity_score >= self.thresholds['high']['min_score']:
            confidence = 'high'
            # Use precision@3 as calibrated probability
            calibrated_prob = self.thresholds['high']['precision_at_3']
        elif similarity_score >= self.thresholds['medium']['min_score']:
            confidence = 'medium'
            calibrated_prob = self.thresholds['medium']['precision_at_3']
        else:
            confidence = 'low'
            calibrated_prob = self.thresholds['low']['precision_at_3']
        
        logger.debug(f"Score {similarity_score:.3f} → {confidence} confidence ({calibrated_prob:.2f})")
        return confidence, calibrated_prob
    
    def compute_calibration(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Compute calibration curve from validation data
        
        Args:
            validation_results: List of validation results with ground truth
            
        Returns:
            Dictionary with calibration statistics and updated thresholds
        """
        if not validation_results:
            logger.warning("No validation results provided")
            return {}
        
        try:
            # Sort by score
            sorted_results = sorted(validation_results, key=lambda x: x.top_score, reverse=True)
            
            # Compute precision@3 for different score thresholds
            score_thresholds = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4]
            calibration_data = []
            
            for threshold in score_thresholds:
                # Filter results above threshold
                above_threshold = [r for r in sorted_results if r.top_score >= threshold]
                
                if not above_threshold:
                    continue
                
                # Compute precision@3
                correct_in_top3 = sum(1 for r in above_threshold if r.in_top_3)
                precision_at_3 = correct_in_top3 / len(above_threshold)
                
                calibration_data.append({
                    'threshold': threshold,
                    'count': len(above_threshold),
                    'precision_at_3': precision_at_3
                })
            
            # Find thresholds for high/medium/low confidence
            # High: precision@3 >= 0.9
            high_threshold = None
            for data in calibration_data:
                if data['precision_at_3'] >= 0.9 and data['count'] >= 10:
                    high_threshold = data['threshold']
                    high_precision = data['precision_at_3']
                    break
            
            # Medium: precision@3 >= 0.7
            medium_threshold = None
            for data in calibration_data:
                if data['precision_at_3'] >= 0.7 and data['count'] >= 20:
                    medium_threshold = data['threshold']
                    medium_precision = data['precision_at_3']
                    break
            
            # Update thresholds if found
            if high_threshold:
                self.thresholds['high']['min_score'] = high_threshold
                self.thresholds['high']['precision_at_3'] = high_precision
            
            if medium_threshold:
                self.thresholds['medium']['min_score'] = medium_threshold
                self.thresholds['medium']['max_score'] = high_threshold if high_threshold else 0.75
                self.thresholds['medium']['precision_at_3'] = medium_precision
            
            # Low is everything below medium
            self.thresholds['low']['max_score'] = medium_threshold if medium_threshold else 0.55
            
            # Compute overall statistics
            total_correct_top3 = sum(1 for r in validation_results if r.in_top_3)
            overall_precision = total_correct_top3 / len(validation_results)
            
            logger.info(f"Calibration complete: {len(validation_results)} samples, "
                       f"overall precision@3: {overall_precision:.3f}")
            
            return {
                'validation_size': len(validation_results),
                'overall_precision_at_3': overall_precision,
                'calibration_curve': calibration_data,
                'thresholds': self.thresholds
            }
            
        except Exception as e:
            logger.error(f"Failed to compute calibration: {e}")
            return {}
    
    def get_confidence_distribution(self, scores: List[float]) -> Dict[str, int]:
        """
        Get distribution of confidence levels for a list of scores
        
        Args:
            scores: List of similarity scores
            
        Returns:
            Dictionary with counts for each confidence level
        """
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for score in scores:
            confidence, _ = self.calibrate_score(score)
            distribution[confidence] += 1
        
        return distribution
