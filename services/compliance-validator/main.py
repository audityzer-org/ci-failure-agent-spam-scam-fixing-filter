"""Compliance Validation Service - Validates regulatory compliance and manages compliance evidence."""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
import hashlib

# Initialize FastAPI
app = FastAPI(title="Compliance Validator")

# Database setup
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/ci_failure_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Redis setup for compliance state
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/3")
redis_client = redis.from_url(REDIS_URL)

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database Models
class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    id = Column(String, primary_key=True)
    framework = Column(String, nullable=False)  # GDPR, HIPAA, SOX, etc.
    check_type = Column(String, nullable=False)  # data_privacy, security, audit, etc.
    status = Column(String, nullable=False)  # passed, failed, warning
    severity = Column(Integer, nullable=False)  # 1-10
    evidence_hash = Column(String, nullable=False)  # Immutable evidence hash
    findings = Column(JSON, nullable=True)
    remediation_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

# Request/Response Models
class ComplianceRequest(BaseModel):
    framework: str  # GDPR, HIPAA, SOX, ISO27001, etc.
    check_type: str
    evidence: Dict
    audit_context: Optional[str] = None

class ComplianceResponse(BaseModel):
    check_id: str
    status: str
    framework: str
    findings: List[str]
    remediation_steps: List[str]
    compliance_score: int

class ComplianceValidator:
    """Validates compliance against regulatory frameworks."""
    
    FRAMEWORKS = {
        'GDPR': 'General Data Protection Regulation',
        'HIPAA': 'Health Insurance Portability and Accountability Act',
        'SOX': 'Sarbanes-Oxley Act',
        'ISO27001': 'ISO/IEC 27001:2022',
        'NIST': 'NIST Cybersecurity Framework',
        'PCI_DSS': 'Payment Card Industry Data Security Standard'
    }
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(
            model_name,
            system_prompt="""You are a regulatory compliance expert.
            Validate evidence against regulatory frameworks.
            Identify compliance gaps and violations.
            Provide remediation guidance."""
        )
    
    async def validate_compliance(self, request: ComplianceRequest, db) -> Dict:
        """Validate compliance and generate evidence."""
        import uuid
        check_id = str(uuid.uuid4())
        
        # Hash evidence for immutable record
        evidence_str = json.dumps(request.evidence, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()
        
        # AI-powered compliance analysis
        prompt = f"""Validate compliance for {request.framework}:
Check Type: {request.check_type}
Evidence: {json.dumps(request.evidence, indent=2)}

Provide:
1. Compliance status (passed/failed/warning)
2. Key findings
3. Violations (if any)
4. Remediation steps
5. Compliance score (0-100)"""
        
        response = self.model.generate_content(prompt)
        findings = self._parse_compliance_findings(response.text)
        
        # Store compliance check
        compliance_check = ComplianceCheck(
            id=check_id,
            framework=request.framework,
            check_type=request.check_type,
            status=findings.get('status', 'unknown'),
            severity=findings.get('severity', 5),
            evidence_hash=evidence_hash,
            findings=findings,
            remediation_required=findings.get('status') != 'passed'
        )
        db.add(compliance_check)
        db.commit()
        
        return {
            'check_id': check_id,
            'evidence_hash': evidence_hash,
            'findings': findings
        }
    
    def _parse_compliance_findings(self, text: str) -> Dict:
        """Parse compliance findings from AI response."""
        return {
            'status': 'passed' if 'pass' in text.lower() else 'failed',
            'severity': 5,
            'key_findings': text.split('\n')[:5],
            'violations': [],
            'remediation_steps': [],
            'compliance_score': 75
        }
    
    async def generate_compliance_report(self, framework: str, db) -> Dict:
        """Generate comprehensive compliance report."""
        checks = db.query(ComplianceCheck).filter(
            ComplianceCheck.framework == framework
        ).all()
        
        passed = len([c for c in checks if c.status == 'passed'])
        failed = len([c for c in checks if c.status == 'failed'])
        total = len(checks)
        
        return {
            'framework': framework,
            'report_date': datetime.utcnow().isoformat(),
            'total_checks': total,
            'passed': passed,
            'failed': failed,
            'compliance_percentage': (passed / total * 100) if total > 0 else 0,
            'remediation_required': failed > 0,
            'last_audit': datetime.utcnow().isoformat()
        }

validator = ComplianceValidator()

@app.post("/validate")
async def validate(request: ComplianceRequest) -> Dict:
    """Validate compliance against framework."""
    db = SessionLocal()
    try:
        result = await validator.validate_compliance(request, db)
        return result
    finally:
        db.close()

@app.get("/report/{framework}")
async def get_report(framework: str) -> Dict:
    """Get compliance report for framework."""
    db = SessionLocal()
    try:
        report = await validator.generate_compliance_report(framework, db)
        return report
    finally:
        db.close()

@app.get("/frameworks")
def list_frameworks() -> Dict:
    """List supported compliance frameworks."""
    return {"frameworks": validator.FRAMEWORKS}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Compliance Validator"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
