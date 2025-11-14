import os
import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import current_app


class ModelLoadError(Exception):
    """Exception raised when models cannot be loaded."""
    pass


class MLService:
    """Simplified Machine Learning service for GDM risk prediction."""
    
    def __init__(self):
        """Initialize ML service."""
        self.model_version = None
        self.is_loaded = False
        self.load_error = None
        self.feature_names = [
            'age', 'bmi', 'systolic_bp', 'diastolic_bp', 'hemoglobin',
            'hdl_cholesterol', 'pregnancies_count', 'family_history_diabetes',
            'sedentary_lifestyle', 'prediabetes_history'
        ]
        
        # Model thresholds from config
        self.threshold_low = current_app.config.get('RISK_THRESHOLD_LOW', 0.33)
        self.threshold_high = current_app.config.get('RISK_THRESHOLD_HIGH', 0.66)
        
        # Initialize the service
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the service (simplified version for development)."""
        try:
            # Set model version
            self.model_version = current_app.config.get('MODEL_VERSION', '1.0.0-dev')
            self.is_loaded = True
            self.load_error = None
            
            logging.info(f"ML Service initialized successfully (development mode: {self.model_version})")
            
        except Exception as e:
            self.is_loaded = False
            self.load_error = str(e)
            logging.error(f"Failed to initialize ML service: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if the ML service is available for predictions."""
        return self.is_loaded
    
    def get_status(self) -> Dict:
        """Get the current status of the ML service."""
        return {
            'is_loaded': self.is_loaded,
            'is_available': self.is_available(),
            'model_version': self.model_version,
            'load_error': self.load_error,
            'feature_count': len(self.feature_names),
            'mode': 'development',
            'thresholds': {
                'low': self.threshold_low,
                'high': self.threshold_high
            }
        }
    
    def validate_input(self, input_data: Dict) -> Tuple[bool, List[str]]:
        """Validate input data for prediction."""
        errors = []
        
        # Check required fields
        required_fields = ['age', 'bmi', 'systolic_bp', 'diastolic_bp', 'pregnancies_count']
        for field in required_fields:
            if field not in input_data or input_data[field] is None:
                errors.append(f"Required field '{field}' is missing")
        
        # Validate value ranges
        if 'age' in input_data and input_data['age'] is not None:
            if not (12 <= input_data['age'] <= 60):
                errors.append("Age must be between 12 and 60 years")
        
        if 'bmi' in input_data and input_data['bmi'] is not None:
            if not (10 <= input_data['bmi'] <= 60):
                errors.append("BMI must be between 10 and 60")
        
        if 'systolic_bp' in input_data and input_data['systolic_bp'] is not None:
            if not (70 <= input_data['systolic_bp'] <= 250):
                errors.append("Systolic BP must be between 70 and 250 mmHg")
        
        if 'diastolic_bp' in input_data and input_data['diastolic_bp'] is not None:
            if not (40 <= input_data['diastolic_bp'] <= 150):
                errors.append("Diastolic BP must be between 40 and 150 mmHg")
        
        if 'pregnancies_count' in input_data and input_data['pregnancies_count'] is not None:
            if not (1 <= input_data['pregnancies_count'] <= 20):
                errors.append("Number of pregnancies must be between 1 and 20")
        
        return len(errors) == 0, errors
    
    def predict_risk(self, input_data: Dict) -> Dict:
        """
        Predict GDM risk based on input clinical data (simplified algorithm).
        
        Args:
            input_data: Dictionary containing clinical features
            
        Returns:
            Dictionary with prediction results
        """
        if not self.is_available():
            raise ModelLoadError(f"ML Service not available: {self.load_error}")
        
        # Validate input
        is_valid, validation_errors = self.validate_input(input_data)
        if not is_valid:
            raise ValueError(f"Invalid input data: {'; '.join(validation_errors)}")
        
        try:
            # Simple rule-based risk calculation for development
            risk_score = self._calculate_risk_score(input_data)
            
            # Determine risk label
            if risk_score < self.threshold_low:
                risk_label = 'LOW'
            elif risk_score < self.threshold_high:
                risk_label = 'MODERATE'
            else:
                risk_label = 'HIGH'
            
            return {
                'risk_score': risk_score,
                'risk_label': risk_label,
                'risk_percentage': round(risk_score * 100, 1),
                'model_version': self.model_version,
                'features_used': input_data.copy(),
                'prediction_timestamp': datetime.utcnow().isoformat(),
                'thresholds': {
                    'low': self.threshold_low,
                    'high': self.threshold_high
                }
            }
            
        except Exception as e:
            logging.error(f"Prediction error: {str(e)}")
            raise RuntimeError(f"Prediction failed: {str(e)}")
    
    def _calculate_risk_score(self, input_data: Dict) -> float:
        """Calculate risk score using simple clinical rules."""
        base_risk = 0.15  # Base risk for all pregnant women
        
        # Age factor
        age = input_data.get('age', 25)
        if age >= 35:
            base_risk += 0.15
        elif age >= 30:
            base_risk += 0.08
        
        # BMI factor
        bmi = input_data.get('bmi', 22)
        if bmi >= 35:
            base_risk += 0.25
        elif bmi >= 30:
            base_risk += 0.15
        elif bmi >= 25:
            base_risk += 0.08
        
        # Blood pressure factor
        systolic_bp = input_data.get('systolic_bp', 110)
        diastolic_bp = input_data.get('diastolic_bp', 70)
        
        if systolic_bp >= 140 or diastolic_bp >= 90:
            base_risk += 0.15
        elif systolic_bp >= 130 or diastolic_bp >= 80:
            base_risk += 0.08
        
        # Family history factor
        if input_data.get('family_history_diabetes', 0) == 1:
            base_risk += 0.20
        
        # Previous pregnancy factor
        pregnancies = input_data.get('pregnancies_count', 1)
        if pregnancies >= 3:
            base_risk += 0.10
        
        # Lifestyle factors
        if input_data.get('sedentary_lifestyle', 0) == 1:
            base_risk += 0.08
        
        # Previous prediabetes
        if input_data.get('prediabetes_history', 0) == 1:
            base_risk += 0.15
        
        # Laboratory values
        hemoglobin = input_data.get('hemoglobin')
        if hemoglobin and hemoglobin < 11:
            base_risk += 0.05
        
        hdl = input_data.get('hdl_cholesterol')
        if hdl and hdl < 40:
            base_risk += 0.05
        
        # Add some controlled randomness for realism
        random.seed(hash(str(sorted(input_data.items()))))  # Deterministic based on input
        noise = random.uniform(-0.05, 0.05)
        base_risk += noise
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_risk))
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance information for the model."""
        return {
            'age': 0.15,
            'bmi': 0.20,
            'systolic_bp': 0.10,
            'diastolic_bp': 0.08,
            'hemoglobin': 0.07,
            'hdl_cholesterol': 0.08,
            'pregnancies_count': 0.12,
            'family_history_diabetes': 0.10,
            'sedentary_lifestyle': 0.05,
            'prediabetes_history': 0.05
        }
    
    def get_reference_ranges(self) -> Dict:
        """Get normal reference ranges for clinical parameters."""
        return {
            'age': {'min': 12, 'max': 60, 'unit': 'years'},
            'bmi': {'min': 18.5, 'max': 24.9, 'unit': 'kg/m²', 'optimal': '18.5-24.9'},
            'systolic_bp': {'min': 90, 'max': 120, 'unit': 'mmHg', 'optimal': '90-120'},
            'diastolic_bp': {'min': 60, 'max': 80, 'unit': 'mmHg', 'optimal': '60-80'},
            'hemoglobin': {'min': 11.5, 'max': 15.0, 'unit': 'g/dL', 'optimal': '11.5-15.0'},
            'hdl_cholesterol': {'min': 40, 'max': 100, 'unit': 'mg/dL', 'optimal': '>40'},
            'pregnancies_count': {'min': 1, 'max': 20, 'unit': 'count'}
        }


# Global ML service instance
ml_service = None


def get_ml_service() -> MLService:
    """Get or create the global ML service instance."""
    global ml_service
    if ml_service is None:
        ml_service = MLService()
    return ml_service


def init_ml_service(app):
    """Initialize ML service with Flask app context."""
    with app.app_context():
        global ml_service
        ml_service = MLService()
        return ml_service