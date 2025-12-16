"""Predictive Suggestions Service - AI-powered failure prediction and actionable recommendations."""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis

# Initialize FastAPI
app = FastAPI(title="Predictive Suggestions Service")

# Database setup
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/ci_failure_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Redis setup for caching suggestions
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/4")
redis_client = redis.from_url(REDIS_URL)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database Models
class PredictiveSuggestion(Base):
    __tablename__ = "predictive_suggestions"
    id = Column(String, primary_key=True)
    failure_pattern = Column(String, nullable=False)
    prediction_confidence = Column(Integer, nullable=False)  # 0-100
    recommended_actions = Column(JSON, nullable=False)
    expected_impact = Column(String, nullable=False)  # high, medium, low
    preventive_measures = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

# Request/Response Models
class PredictionRequest(BaseModel):
    failure_pattern: str
    historical_data: Dict
    context: Optional[str] = None

class SuggestionResponse(BaseModel):
    suggestion_id: str
    prediction_confidence: int
    recommended_actions: List[str]
    expected_impact: str
    preventive_measures: List[str]
    created_at: str

class PredictiveSuggestionsEngine:
    """AI-powered predictive suggestions engine for CI/CD failures."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(
            model_name,
            system_prompt="""You are an expert CI/CD failure prediction AI.
            Analyze patterns and predict failures before they occur.
            Provide actionable recommendations and preventive measures.
            Format responses as JSON with: prediction_confidence (0-100), recommended_actions (list), 
            expected_impact (high/medium/low), preventive_measures (list)."""
        )
    
    async def predict_failure(self, request: PredictionRequest, db) -> Dict:
        """Predict potential CI/CD failures and suggest preventive actions."""
        import uuid
        suggestion_id = str(uuid.uuid4())
        
        # Check cache first
        cache_key = f"prediction:{hash(request.failure_pattern) % 10000}"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # AI-powered prediction
        prompt = f"""Analyze this CI/CD failure pattern and predict future failures:
        Pattern: {request.failure_pattern}
        Historical Data: {json.dumps(request.historical_data, indent=2)}
        Context: {request.context or 'General CI/CD environment'}
        
        Provide JSON response with:
        1. prediction_confidence: 0-100 scale
        2. recommended_actions: list of immediate actions
        3. expected_impact: high/medium/low
        4. preventive_measures: list of preventive steps"""
        
        response = self.model.generate_content(prompt)
        
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {
                'prediction_confidence': 60,
                'recommended_actions': ['Review logs', 'Monitor system health'],
                'expected_impact': 'medium',
                'preventive_measures': ['Implement monitoring', 'Add alerting']
            }
        
        # Store prediction
        prediction = PredictiveSuggestion(
            id=suggestion_id,
            failure_pattern=request.failure_pattern,
            prediction_confidence=result.get('prediction_confidence', 50),
            recommended_actions=result.get('recommended_actions', []),
            expected_impact=result.get('expected_impact', 'medium'),
            preventive_measures=result.get('preventive_measures', [])
        )
        db.add(prediction)
        db.commit()
        
        # Cache result for 24 hours
        output = {
            'suggestion_id': suggestion_id,
            'prediction_confidence': result.get('prediction_confidence', 50),
            'recommended_actions': result.get('recommended_actions', []),
            'expected_impact': result.get('expected_impact', 'medium'),
            'preventive_measures': result.get('preventive_measures', [])
        }
        redis_client.setex(cache_key, 86400, json.dumps(output))
        
        return output
    
    async def get_high_confidence_predictions(self, min_confidence: int, db) -> List:
        """Get all high-confidence predictions."""
        predictions = db.query(PredictiveSuggestion).filter(
            PredictiveSuggestion.prediction_confidence >= min_confidence
        ).all()
        return [{
            'id': p.id,
            'pattern': p.failure_pattern,
            'confidence': p.prediction_confidence,
            'actions': p.recommended_actions
        } for p in predictions]

engine_instance = PredictiveSuggestionsEngine()

@app.post("/predict", response_model=SuggestionResponse)
async def predict(request: PredictionRequest) -> SuggestionResponse:
    """Get predictive suggestions for CI/CD failures."""
    db = SessionLocal()
    try:
        result = await engine_instance.predict_failure(request, db)
        return SuggestionResponse(
            suggestion_id=result['suggestion_id'],
            prediction_confidence=result['prediction_confidence'],
            recommended_actions=result['recommended_actions'],
            expected_impact=result['expected_impact'],
            preventive_measures=result['preventive_measures'],
            created_at=datetime.utcnow().isoformat()
        )
    finally:
        db.close()

@app.get("/predictions/high-confidence")
async def get_high_confidence(min_confidence: int = 75) -> Dict:
    """Get high-confidence predictions."""
    db = SessionLocal()
    try:
        predictions = await engine_instance.get_high_confidence_predictions(min_confidence, db)
        return {"predictions": predictions, "count": len(predictions)}
    finally:
        db.close()

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Predictive Suggestions Service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
