# API Documentation and Integration Guide

## Overview
This document provides comprehensive API documentation for the CI Failure Agent and integration patterns for auditorsec.com and audityzer.com platforms.

## Table of Contents
1. [API Endpoints](#api-endpoints)
2. [Authentication](#authentication)
3. [Request/Response Formats](#requestresponse-formats)
4. [Error Handling](#error-handling)
5. [Integration Examples](#integration-examples)
6. [Rate Limiting](#rate-limiting)
7. [Webhook Management](#webhook-management)
8. [SDK Usage](#sdk-usage)

## API Endpoints

### Base URL
```
Production: https://api.audityzer.com/v1
Staging: https://staging-api.audityzer.com/v1
Development: http://localhost:3000/v1
```

### Core Endpoints

#### 1. Health Check
```
GET /health
Description: Verify API availability and status
Response: {"status": "healthy", "timestamp": "ISO8601", "version": "1.0.0"}
Status Code: 200 OK
```

#### 2. Spam Detection
```
POST /spam/detect
Description: Analyze content for spam patterns
Authentication: Bearer token
Request Body:
{
  "content": "text to analyze",
  "context": "email|comment|review",
  "user_id": "optional-user-uuid",
  "metadata": {
    "ip_address": "optional",
    "user_agent": "optional",
    "timestamp": "optional-iso8601"
  }
}
Response:
{
  "is_spam": boolean,
  "confidence": 0.0-1.0,
  "risk_score": 0-100,
  "categories": ["phishing", "malware", "advertising"],
  "patterns_detected": ["suspicious_url", "repeated_keywords"],
  "recommendations": ["block", "quarantine", "review"]
}
Status Codes:
- 200 OK: Analysis successful
- 400 Bad Request: Invalid input
- 401 Unauthorized: Authentication failed
- 429 Too Many Requests: Rate limit exceeded
```

#### 3. Batch Analysis
```
POST /spam/batch
Description: Analyze multiple items in one request
Authentication: Bearer token
Request Body:
{
  "items": [
    {"id": "item-1", "content": "text..."},
    {"id": "item-2", "content": "text..."}
  ],
  "callback_url": "optional-webhook-url"
}
Response:
{
  "batch_id": "batch-uuid",
  "status": "processing|completed",
  "items_count": 2,
  "processed_count": 2,
  "results": []
}
```

#### 4. User Reports
```
POST /reports/submit
Description: Submit user abuse reports
Authentication: Bearer token
Request Body:
{
  "reported_content_id": "content-uuid",
  "reason": "spam|abuse|harassment|violence",
  "description": "detailed description",
  "reporter_id": "user-uuid"
}
Response:
{
  "report_id": "report-uuid",
  "status": "submitted",
  "created_at": "ISO8601"
}
```

#### 5. Analytics
```
GET /analytics/summary
Description: Get spam detection statistics
Authentication: Bearer token
Query Parameters:
- from: ISO8601 timestamp (required)
- to: ISO8601 timestamp (required)
- granularity: hour|day|week|month (default: day)
Response:
{
  "total_analyzed": 10000,
  "spam_detected": 1250,
  "spam_rate": 12.5,
  "categories_breakdown": {...},
  "trend_data": [...]
}
```

## Authentication

### API Key Authentication
```
Header: Authorization: Bearer YOUR_API_KEY
```

### OAuth 2.0 Flow
```
1. GET /oauth/authorize?client_id=...&redirect_uri=...&scope=...
2. User grants permission
3. POST /oauth/token with authorization code
4. Receive access token (expires in 3600 seconds)
5. Refresh token for continuous access
```

### JWT Tokens
```
Payload Structure:
{
  "iss": "audityzer.com",
  "sub": "user-id",
  "aud": "api.audityzer.com",
  "exp": 1234567890,
  "iat": 1234567200,
  "scopes": ["read", "write", "admin"]
}
```

## Request/Response Formats

### Standard Request Headers
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer TOKEN
X-Request-ID: unique-request-id (optional)
X-Client-Version: 1.0.0 (optional)
```

### Standard Response Format
```json
{
  "success": true,
  "data": { /* endpoint-specific data */ },
  "meta": {
    "request_id": "unique-id",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "SPAM_DETECTION_FAILED",
    "message": "Human readable error message",
    "details": { /* additional error context */ }
  },
  "meta": {
    "request_id": "unique-id",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Error Handling

### HTTP Status Codes
- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid parameters
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Codes
```
INVALID_REQUEST - Malformed request
AUTHENTICATION_FAILED - Invalid credentials
RATE_LIMIT_EXCEEDED - Too many requests
QUOTA_EXCEEDED - Usage quota exceeded
SERVICE_UNAVAILABLE - Service down for maintenance
INTERNAL_ERROR - Unexpected server error
```

## Integration Examples

### JavaScript/Node.js
```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://api.audityzer.com/v1',
  headers: {
    'Authorization': `Bearer ${process.env.API_KEY}`,
    'Content-Type': 'application/json'
  }
});

// Detect spam
async function detectSpam(content) {
  try {
    const response = await client.post('/spam/detect', {
      content: content,
      context: 'comment'
    });
    return response.data;
  } catch (error) {
    console.error('Spam detection error:', error.response.data);
    throw error;
  }
}

module.exports = { detectSpam };
```

### Python
```python
import requests
from typing import Dict, Any

class AuditzerAPI:
    def __init__(self, api_key: str):
        self.base_url = 'https://api.audityzer.com/v1'
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def detect_spam(self, content: str, context: str = 'comment') -> Dict[str, Any]:
        response = requests.post(
            f'{self.base_url}/spam/detect',
            json={'content': content, 'context': context},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def batch_analysis(self, items: list, callback_url: str = None) -> Dict[str, Any]:
        response = requests.post(
            f'{self.base_url}/spam/batch',
            json={'items': items, 'callback_url': callback_url},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
```

### cURL Examples
```bash
# Health check
curl -X GET https://api.audityzer.com/v1/health

# Detect spam
curl -X POST https://api.audityzer.com/v1/spam/detect \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Buy cheap viagra now!!!",
    "context": "email"
  }'

# Batch analysis
curl -X POST https://api.audityzer.com/v1/spam/batch \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id": "1", "content": "text1"},
      {"id": "2", "content": "text2"}
    ]
  }'
```

## Rate Limiting

### Limits by Plan
- **Free Tier**: 100 requests/hour, 1,000 requests/day
- **Professional**: 10,000 requests/hour, 100,000 requests/day
- **Enterprise**: Custom limits

### Rate Limit Headers
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9999
X-RateLimit-Reset: 1234567890
X-RateLimit-Retry-After: 60
```

### Handling Rate Limits
```javascript
if (response.status === 429) {
  const retryAfter = response.headers['x-ratelimit-retry-after'];
  // Wait and retry after specified seconds
  setTimeout(() => retry(), retryAfter * 1000);
}
```

## Webhook Management

### Register Webhook
```
POST /webhooks/register
Request:
{
  "url": "https://yoursite.com/webhook",
  "events": ["spam.detected", "analysis.completed"],
  "secret": "webhook-secret-key"
}
Response:
{
  "webhook_id": "wh-uuid",
  "status": "active"
}
```

### Webhook Events
```
spam.detected - Spam content identified
analysis.completed - Batch analysis finished
report.submitted - User report received
quota.warning - Approaching usage limits
```

### Webhook Payload Signature
```
X-Signature: sha256=SIGNATURE_VALUE
```

## SDK Usage

### Installation
```bash
npm install @audityzer/api-sdk
# or
pip install audityzer-api
```

### Quick Start
```javascript
const Audityzer = require('@audityzer/api-sdk');

const client = new Audityzer({
  apiKey: process.env.AUDITYZER_API_KEY,
  environment: 'production'
});

const result = await client.spam.detect({
  content: 'User submitted content',
  context: 'review'
});
```

## Support and Resources
- Documentation: https://docs.audityzer.com
- Support: support@audityzer.com
- Status Page: https://status.audityzer.com
- GitHub: https://github.com/audityzer-org

---
Last Updated: 2024-01-15
Version: 1.0.0
Author: Audityzer Development Team
