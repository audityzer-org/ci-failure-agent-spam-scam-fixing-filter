"""CI Failure Agent - Multi-agent AI system for automated CI/CD failure analysis and workflow optimization."""

import os
import json
import asyncio
from typing import Optional, Dict

import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI(title="CI Failure Agent")

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class FailureAnalysisRequest(BaseModel):
    logs: str
    workflow_name: str
    repository: Optional[str] = None

class CIFailureAgent:
    """Multi-agent system for analyzing CI/CD failures."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model = genai.GenerativeModel(
            model_name,
            system_prompt="You are an expert CI/CD failure analysis agent. "
            "Analyze GitHub Actions logs, detect failures, and propose fixes."
        )
    
    async def analyze_failure(self, logs: str, workflow: str) -> Dict:
        """Analyze CI/CD failure logs and return structured analysis."""
        prompt = f"Analyze {workflow} CI/CD failure logs and return root_cause, category, severity, fixes: {logs}"
        response = self.model.generate_content(prompt)
        return {"analysis": response.text}

agent = CIFailureAgent()

@app.post("/analyze")
async def analyze_ci_failure(request: FailureAnalysisRequest) -> Dict:
    """Endpoint to analyze CI/CD failures."""
    result = await agent.analyze_failure(request.logs, request.workflow_name)
    return {"status": "analyzed", "result": result}

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CI Failure Agent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
