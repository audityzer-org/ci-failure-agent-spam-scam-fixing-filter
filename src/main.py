"""CI Failure Agent - Multi-agent AI system for automated CI/CD failure analysis and workflow optimization."""
import os
import json
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="CI Failure Agent", version="1.0.0")

# Configure Gemini API with error handling
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
    else:
        logger.warning("GOOGLE_API_KEY not set - some features will be limited")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {str(e)}")

class FailureAnalysisRequest(BaseModel):
    logs: str
    workflow_name: str
    repository: Optional[str] = None

class CIFailureAgent:
    """Multi-agent system for analyzing CI/CD failures."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        try:
            self.model = genai.GenerativeModel(
                model_name,
                system_prompt="You are an expert CI/CD failure analysis agent. "
                "Analyze GitHub Actions logs, detect failures, and propose fixes."
            )
            logger.info(f"Initialized {model_name} model")
        except Exception as e:
            logger.error(f"Failed to initialize model: {str(e)}")
            self.model = None
    
    async def analyze_failure(self, logs: str, workflow: str) -> Dict:
        """Analyze CI/CD failure logs and return structured analysis."""
        try:
            if not self.model:
                return {
                    "status": "warning",
                    "message": "Model not initialized. Please set GOOGLE_API_KEY.",
                    "timestamp": datetime.now().isoformat()
                }
            
            prompt = f"Analyze {workflow} CI/CD failure logs and return root_cause, category, severity, fixes: {logs[:5000]}"
            response = self.model.generate_content(prompt, generation_config={"max_output_tokens": 1000})
            
            logger.info(f"Successfully analyzed failure for workflow: {workflow}")
            return {
                "analysis": response.text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing failure: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

agent = CIFailureAgent()

@app.post("/analyze")
async def analyze_ci_failure(request: FailureAnalysisRequest) -> Dict:
    """Endpoint to analyze CI/CD failures."""
    try:
        logger.info(f"Analyzing failure for workflow: {request.workflow_name}")
        result = await agent.analyze_failure(request.logs, request.workflow_name)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Failed to process analysis request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CI Failure Agent",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/info")
def info():
    """Get service information."""
    return {
        "name": "CI Failure Agent",
        "version": "1.0.0",
        "description": "Multi-agent AI system for automated CI/CD failure analysis",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "CI Failure Agent API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting CI Failure Agent")
    uvicorn.run(app, host="0.0.0.0", port=8000)
