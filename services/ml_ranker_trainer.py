"""ML Ranker Trainer for Predictive Action Ranking

This module collects user feedback on recommended actions and trains
an ML model to improve action ranking accuracy over time.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ActionFeedback:
    """Represents user feedback on a recommended action."""
    action_id: str
    alert_type: str
    alert_severity: str
    action_name: str
    user_decision: str  # 'accepted', 'rejected', 'ignored'
    action_outcome: str  # 'successful', 'failed', 'pending'
    timestamp: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)


class MLRankerTrainer:
    """Trains ML models for action ranking based on user feedback."""

    def __init__(self, model_path: str = "./models/action_ranker.pkl"):
        self.model_path = model_path
        self.model = None
        self.label_encoders = {}
        self.feature_names = ['alert_type', 'severity', 'action_type', 'outcome']
        self.feedback_history = []
        self.logger = logging.getLogger(__name__)

    async def collect_feedback(self, feedback: ActionFeedback) -> None:
        """Collect and store user feedback on actions."""
        try:
            self.feedback_history.append(feedback)
            self.logger.info(f"Feedback collected: {feedback.action_id}")
            await self._save_feedback(feedback)
        except Exception as e:
            self.logger.error(f"Error collecting feedback: {str(e)}")

    async def _save_feedback(self, feedback: ActionFeedback) -> None:
        """Save feedback to database or file."""
        # Implementation depends on storage backend
        # For now, log it
        self.logger.debug(f"Saved feedback: {feedback.to_dict()}")

    def prepare_training_data(self, feedback_list: List[ActionFeedback]) -> tuple:
        """Prepare features and labels from feedback data."""
        features = []
        labels = []

        for feedback in feedback_list:
            feature_vector = [
                feedback.alert_type,
                feedback.alert_severity,
                feedback.action_name,
                feedback.action_outcome
            ]
            features.append(feature_vector)
            # Label: 1 if accepted, 0 if not
            label = 1 if feedback.user_decision == 'accepted' else 0
            labels.append(label)

        return np.array(features), np.array(labels)

    def _encode_features(self, features: np.ndarray) -> np.ndarray:
        """Encode categorical features."""
        encoded = []
        for i, feature_name in enumerate(self.feature_names):
            if feature_name not in self.label_encoders:
                self.label_encoders[feature_name] = LabelEncoder()
                col_data = features[:, i].reshape(-1, 1)
                self.label_encoders[feature_name].fit(col_data.flatten())
            
            col_data = features[:, i].reshape(-1, 1)
            encoded_col = self.label_encoders[feature_name].transform(col_data.flatten())
            encoded.append(encoded_col)
        
        return np.column_stack(encoded)

    async def train_model(self, feedback_list: List[ActionFeedback]) -> Dict[str, Any]:
        """Train ML model on collected feedback."""
        try:
            if len(feedback_list) < 10:
                self.logger.warning("Insufficient feedback data for training")
                return {"status": "insufficient_data", "samples": len(feedback_list)}

            features, labels = self.prepare_training_data(feedback_list)
            encoded_features = self._encode_features(features)

            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.model.fit(encoded_features, labels)
            
            # Save model
            joblib.dump(self.model, self.model_path)
            self.logger.info(f"Model trained and saved to {self.model_path}")

            return {
                "status": "success",
                "samples": len(feedback_list),
                "accuracy": self.model.score(encoded_features, labels)
            }
        except Exception as e:
            self.logger.error(f"Error training model: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def predict_action_score(self, alert_type: str, severity: str, 
                                    action_name: str) -> float:
        """Predict probability of action acceptance."""
        if self.model is None:
            self.logger.warning("Model not trained yet")
            return 0.5

        try:
            features = np.array([[alert_type, severity, action_name, 'pending']])
            encoded = self._encode_features(features)
            probability = self.model.predict_proba(encoded)[0][1]
            return float(probability)
        except Exception as e:
            self.logger.error(f"Error predicting score: {str(e)}")
            return 0.5

    async def rank_actions(self, alert_type: str, severity: str, 
                          actions: List[Dict]) -> List[Dict]:
        """Rank actions by probability of acceptance."""
        ranked_actions = []

        for action in actions:
            score = await self.predict_action_score(
                alert_type, severity, action['name']
            )
            ranked_actions.append({
                **action,
                'ml_confidence': score,
                'ml_rank': len(ranked_actions) + 1
            })

        # Sort by ML confidence
        ranked_actions.sort(key=lambda x: x['ml_confidence'], reverse=True)
        
        # Update ranks
        for i, action in enumerate(ranked_actions):
            action['ml_rank'] = i + 1

        return ranked_actions

    def get_model_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        return {
            "model_path": self.model_path,
            "feedback_samples": len(self.feedback_history),
            "model_trained": self.model is not None,
            "feature_names": self.feature_names
        }
