"""Spam and Scam Detection Microservice - Detects spam, phishing, and scam patterns in CI/CD logs."""
import os
import json
import redis
from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Initialize FastAPI
app = FastAPI(title="Spam Detection Service")

# Database setup
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/ci_failure_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Redis setup
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
redis_client = redis.from_url(REDIS_URL)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database Models
class SpamReport(Base):
    __tablename__ = "spam_reports"
    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    classification = Column(String, nullable=False)
    confidence = Column(Integer, nullable=False)
    detected_patterns = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# Request/Response Models
class SpamDetectionRequest(BaseModel):
    content: str
    context: Optional[str] = None
    threshold: int = 50

class SpamDetectionResponse(BaseModel):
    is_spam: bool
    confidence: int
    classification: str
    patterns_detected: List[str]
    recommendation: str

class SpamDetector:
    """AI-powered spam and scam detection system."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(
            model_name,
            system_prompt="You are an expert spam and scam detection AI. "
            "Analyze text for phishing, spam, scams, and malicious patterns. "
            "Provide detailed classification and confidence scores."
        )
        self.spam_patterns = {
            'phishing': ['verify account', 'confirm identity', 'click here', 'urgent action'],
            'malware': ['download now', 'install software', 'execute script'],
            'financial_scam': ['wire transfer', 'bitcoin', 'claim prize', 'inheritance'],
            'credential_theft': ['username', 'password', 'credentials', 'token']
        }
    
    async def detect(self, content: str, context: Optional[str] = None) -> Dict:
        """Detect spam and scam patterns in content."""
        # Check cache first
        cache_key = f"spam:{hash(content) % 10000}"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Analyze with AI
        prompt = f"""Analyze this content for spam/scam:
{content}

Context: {context or 'General text analysis'}

Provide JSON response with:
- is_spam: boolean
- confidence: 0-100
- classification: phishing|malware|financial_scam|credential_theft|legitimate
- patterns: list of detected patterns
- recommendation: action to take"""
        
        response = self.model.generate_content(prompt)
        
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {
                'is_spam': False,
                'confidence': 0,
                'classification': 'parse_error',
                'patterns': [],
                'recommendation': 'Manual review required'
            }
        
        # Cache result for 1 hour
        redis_client.setex(cache_key, 3600, json.dumps(result))
        
        return result

detector = SpamDetector()

@app.post("/detect", response_model=SpamDetectionResponse)
async def detect_spam(request: SpamDetectionRequest) -> SpamDetectionResponse:
    """Detect spam/scam content."""
    result = await detector.detect(request.content, request.context)
    
    # Store in database
    db = SessionLocal()
    try:
        report = SpamReport(
            content=request.content[:500],
            classification=result.get('classification', 'unknown'),
            confidence=result.get('confidence', 0),
            detected_patterns=json.dumps(result.get('patterns', []))
        )
        db.add(report)
        db.commit()
    finally:
        db.close()
    
    return SpamDetectionResponse(
        is_spam=result.get('is_spam', False),
        confidence=result.get('confidence', 0),
        classification=result.get('classification', 'unknown'),
        patterns_detected=result.get('patterns', []),
        recommendation=result.get('recommendation', 'Review content manually')
    )

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Spam Detection Service"}

@app.get("/stats")
def get_statistics():
    """Get spam detection statistics."""
    db = SessionLocal()
    try:
        total_scanned = db.query(SpamReport).count()
        spam_detected = db.query(SpamReport).filter(SpamReport.classification != 'legitimate').count()
        
        return {
            "total_scanned": total_scanned,
            "spam_detected": spam_detected,
            "accuracy": f"{(spam_detected / max(total_scanned, 1)) * 100:.2f}%"
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
