# Security Hardening and Compliance Document

## Overview
This document outlines comprehensive security hardening practices, compliance requirements, and security policies for the Audityzer CI/CD infrastructure on AWS EKS.

## Table of Contents
1. [Security Architecture](#security-architecture)
2. [Kubernetes Security](#kubernetes-security)
3. [Network Security](#network-security)
4. [IAM and Access Control](#iam-and-access-control)
5. [Data Encryption](#data-encryption)
6. [Compliance Standards](#compliance-standards)
7. [Vulnerability Management](#vulnerability-management)
8. [Incident Response](#incident-response)

## Security Architecture

### Defense-in-Depth Strategy
```
Layer 1: Network Security (VPC, Security Groups)
Layer 2: Container Security (Image scanning, Runtime)
Layer 3: Application Security (Code scanning, Dependencies)
Layer 4: Data Security (Encryption, Access Control)
Layer 5: Monitoring and Detection (Logging, Alerting)
```

### Security Zones
```
DMZ Zone: ALB, WAF, API Gateway
Application Zone: EKS Cluster, Microservices
Data Zone: RDS, Elasticache, S3 with encryption
Management Zone: CI/CD Pipeline, Logging, Monitoring
```

## Kubernetes Security

### RBAC Configuration
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-reader
subjects:
- kind: User
  name: user@audityzer.com
  apiGroup: rbac.authorization.k8s.io
```

### Pod Security Policies
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
    seLinuxOptions:
      level: "s0:c123,c456"
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
```

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-api
spec:
  podSelector:
    matchLabels:
      tier: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: frontend
    ports:
    - protocol: TCP
      port: 8080
```

## Network Security

### VPC Configuration
```hcl
# Main VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "audityzer-vpc"
    Environment = "production"
    Security = "high"
  }
}

# Security Groups
resource "aws_security_group" "eks_master" {
  name_prefix = "eks-master-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Restrict to bastion/specific IPs
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### WAF Configuration
```hcl
resource "aws_wafv2_web_acl" "main" {
  name  = "audityzer-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "audityzer-waf"
    sampled_requests_enabled   = true
  }
}
```

## IAM and Access Control

### Role-Based Access Control (RBAC)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EKSClusterAccess",
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:DescribeImages"
      ],
      "Resource": "arn:aws:ecr:*:*:repository/*"
    },
    {
      "Sid": "DenyHighRiskActions",
      "Effect": "Deny",
      "Action": [
        "iam:DeleteRole",
        "iam:DeleteUser",
        "iam:DeleteAccessKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### MFA Enforcement
```python
import boto3

def check_mfa_enabled(iam_client):
    users = iam_client.list_users()['Users']
    for user in users:
        mfa_devices = iam_client.list_mfa_devices(UserName=user['UserName'])
        if not mfa_devices['MFADevices']:
            print(f"Warning: User {user['UserName']} has no MFA enabled")
```

## Data Encryption

### Encryption at Rest
```hcl
# RDS Encryption
resource "aws_db_instance" "main" {
  allocated_storage    = 100
  storage_type         = "gp3"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.micro"
  
  # Encryption
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.main.arn
  
  # Backup
  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  
  # Security
  publicly_accessible = false
  skip_final_snapshot = false
}

# S3 Encryption
resource "aws_s3_bucket" "logs" {
  bucket = "audityzer-logs"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
  }
}
```

### Encryption in Transit
```yaml
# TLS Configuration in Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secure-ingress
spec:
  tls:
  - hosts:
    - audityzer.com
    - api.audityzer.com
    secretName: audityzer-tls-cert
  rules:
  - host: audityzer.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 443
```

## Compliance Standards

### GDPR Compliance
- Data Location: EU region (Ireland)
- Data Retention: 30 days minimum, configurable
- Right to Deletion: Automated purge policies
- Privacy: PII encryption with customer-managed keys
- Audit Logging: All data access logged

### SOC 2 Compliance
- Access Control: RBAC with MFA
- Change Management: Automated via GitOps
- Encryption: AES-256 at rest, TLS 1.2+ in transit
- Monitoring: 24/7 CloudWatch monitoring
- Incident Response: Automated alerts and playbooks

### Security Checklist
```
[ ] Enable EKS audit logging
[ ] Configure VPC Flow Logs
[ ] Enable CloudTrail for API auditing
[ ] Implement Network ACLs
[ ] Configure Security Groups with least privilege
[ ] Enable container image scanning
[ ] Implement pod security policies
[ ] Enable encryption for all data stores
[ ] Configure IAM role separation
[ ] Enable MFA for all human users
[ ] Regular security patching schedule
[ ] Implement DLP for sensitive data
```

## Vulnerability Management

### Container Image Scanning
```bash
#!/bin/bash
# Scan ECR images for vulnerabilities

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="eu-west-1"

aws ecr describe-images \
  --repository-name audityzer-api \
  --region $REGION \
  --query 'imageDetails[*].[imageTags[0],imageSizeInBytes]'

# Trigger image scan
aws ecr start-image-scan \
  --repository-name audityzer-api \
  --image-id imageTag=latest \
  --region $REGION

# Get scan results
aws ecr describe-image-scan-findings \
  --repository-name audityzer-api \
  --image-id imageTag=latest \
  --region $REGION
```

### Dependency Scanning
```yaml
# GitHub Actions Workflow for dependency scanning
name: Security Scanning
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'audityzer'
          path: '.'
          format: 'JSON'
      
      - name: Run Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
```

## Incident Response

### Incident Response Plan
1. **Detection**: Automated via CloudWatch, GuardDuty
2. **Response**: Immediate isolation of affected resources
3. **Investigation**: Forensic analysis with CloudTrail logs
4. **Remediation**: Automated remediation where possible
5. **Communication**: Notification to stakeholders
6. **Post-Mortem**: RCA and process improvements

### Runbook: Data Breach
```bash
#!/bin/bash
# Incident Response: Potential Data Breach

echo "[1] Isolating affected pod..."
kubectl delete pod POD_NAME -n production

echo "[2] Capturing logs for forensics..."
kubectl logs POD_NAME -n production > /tmp/forensics.log

echo "[3] Checking CloudTrail for unauthorized access..."
aws cloudtrail lookup-events --max-results 50

echo "[4] Enabling flow logs for investigation..."
aws ec2 create-flow-logs \
  --resource-type NetworkInterface \
  --traffic-type ALL

echo "[5] Alerting security team..."
send_alert "CRITICAL: Potential data breach detected"
```

---
Last Updated: 2024-01-15
Version: 1.0.0
Author: Audityzer Security Team
