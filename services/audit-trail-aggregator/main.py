"""Audit Trail Aggregator - Centralizes and manages audit logs from all services."""
import os
import json
from typing import Dict, List
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="Audit Trail Aggregator")

DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/ci_failure_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    service = Column(String, nullable=False)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    severity = Column(Integer, default=0)

Base.metadata.create_all(engine)

class AuditEventRequest(BaseModel):
    service: str
    action: str
    actor: str
    resource: str
    details: Dict
    severity: int = 0

class AuditAggregator:
    """Aggregates audit events from all services."""
    
    async def log_event(self, request: AuditEventRequest, db) -> str:
        """Log audit event."""
        import uuid
        log_id = str(uuid.uuid4())
        
        audit_log = AuditLog(
            id=log_id,
            service=request.service,
            action=request.action,
            actor=request.actor,
            resource=request.resource,
            status="recorded",
            details=request.details,
            severity=request.severity
        )
        db.add(audit_log)
        db.commit()
        return log_id
    
    async def get_audit_trail(self, service: str, limit: int, db) -> List:
        """Get audit trail for service."""
        logs = db.query(AuditLog).filter(
            AuditLog.service == service
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [{
            'id': log.id,
            'action': log.action,
            'actor': log.actor,
            'created_at': log.created_at.isoformat(),
            'details': log.details
        } for log in logs]

aggregator = AuditAggregator()

@app.post("/log")
async def log_audit_event(request: AuditEventRequest) -> Dict:
    """Log audit event."""
    db = SessionLocal()
    try:
        log_id = await aggregator.log_event(request, db)
        return {"log_id": log_id, "status": "logged"}
    finally:
        db.close()

@app.get("/trail/{service}")
async def get_trail(service: str, limit: int = 100) -> Dict:
    """Get audit trail."""
    db = SessionLocal()
    try:
        trail = await aggregator.get_audit_trail(service, limit, db)
        return {"service": service, "logs": trail}
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "Audit Trail Aggregator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
