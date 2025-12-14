# Phase 2 Implementation Guide: Domain & SSL/TLS Configuration

## Overview
Phase 2 focuses on setting up a custom domain, configuring DNS, and implementing SSL/TLS certificates for the CI Failure Agent application running on Kubernetes.

**Timeline**: December 23-27, 2025 (1 week)
**Status**: 📅 SCHEDULED
**Priority**: HIGH
**Dependencies**: Phase 1 EKS cluster must be operational

---

## Phase 2 Objectives

1. **Domain Registration** - Register custom domain (anti-corruption-agent.tech or alternative)
2. **DNS Configuration** - Set up DNS records pointing to Kubernetes ingress
3. **cert-manager Installation** - Deploy cert-manager on Kubernetes
4. **Let's Encrypt Setup** - Configure automated certificate provisioning
5. **TLS Ingress Configuration** - Set up secure ingress with HTTPS
6. **Security Headers** - Configure HSTS, CSP, and other security headers

---

## Step 1: Domain Registration

### 1.1 Domain Selection

**Recommended domain**: `ci-failure-agent.io` or `anti-corruption-agent.tech`

**Domain Registrars**:
- Route 53 (AWS) - $12/year
- Namecheap - $8.88/year
- GoDaddy - $12.99/year

### 1.2 Registration Steps

```bash
# If using Route 53
aws route53 create-hosted-zone \
  --name ci-failure-agent.io \
  --caller-reference $(date +%s)

# Get nameserver details
aws route53 list-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --query 'ResourceRecordSets[?Type==`NS`]'
```

---

## Step 2: DNS Configuration

### 2.1 Kubernetes Ingress IP

First, get the external IP of the NGINX ingress controller:

```bash
# Get ingress IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Note the EXTERNAL-IP
# This will be used for DNS A record
```

### 2.2 DNS A Record Setup

```yaml
# Using AWS Route 53
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch file://dns-records.json
```

**dns-records.json**:
```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "ci-failure-agent.io",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<INGRESS_EXTERNAL_IP>"}]
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.ci-failure-agent.io",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "ci-failure-agent.io"}]
      }
    }
  ]
}
```

### 2.3 Verify DNS Propagation

```bash
# Wait for DNS to propagate (5-15 minutes typical)
nslookup ci-failure-agent.io
dig ci-failure-agent.io
curl http://ci-failure-agent.io/health
```

---

## Step 3: cert-manager Installation

### 3.1 Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true \
  --version v1.13.2

# Verify installation
kubectl get pods -n cert-manager
kubectl api-resources | grep cert-manager.io
```

### 3.2 Create ClusterIssuer for Let's Encrypt

```yaml
# File: k8s/letsencrypt-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@ci-failure-agent.io
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@ci-failure-agent.io
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
      - http01:
          ingress:
            class: nginx
```

```bash
# Deploy issuers
kubectl apply -f k8s/letsencrypt-issuer.yaml

# Verify issuers
kubectl get clusterissuer
kubectl describe clusterissuer letsencrypt-prod
```

---

## Step 4: TLS Ingress Configuration

### 4.1 Create HTTPS Ingress

```yaml
# File: k8s/ingress-https.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - ci-failure-agent.io
        - www.ci-failure-agent.io
      secretName: ci-failure-agent-tls
  rules:
    - host: ci-failure-agent.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ci-failure-agent-service
                port:
                  number: 80
    - host: www.ci-failure-agent.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ci-failure-agent-service
                port:
                  number: 80
```

```bash
# Deploy ingress
kubectl apply -f k8s/ingress-https.yaml

# Check ingress status
kubectl get ingress
kubectl describe ingress ci-failure-agent-ingress

# Monitor certificate creation
kubectl get certificate
kubectl get certificaterequest
kubectl describe certificate ci-failure-agent-tls
```

### 4.2 Verify SSL Certificate

```bash
# Test HTTPS endpoint (wait 2-5 minutes for cert generation)
curl -I https://ci-failure-agent.io

# Check certificate details
openssl s_client -connect ci-failure-agent.io:443

# Verify certificate chain
echo | openssl s_client -servername ci-failure-agent.io -connect ci-failure-agent.io:443 | openssl x509 -text
```

---

## Step 5: Security Headers Configuration

### 5.1 NGINX Security Headers

```yaml
# File: k8s/ingress-security-headers.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-secure
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    # SSL/TLS Configuration
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.2 TLSv1.3"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE+AESGCM:ECDHE+AES256:ECDHE+AES128:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA"
    # Security Headers
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
      more_set_headers "Permissions-Policy: geolocation=(), microphone=(), camera=()";
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://ci-failure-agent.io"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - ci-failure-agent.io
        - www.ci-failure-agent.io
      secretName: ci-failure-agent-tls
  rules:
    - host: ci-failure-agent.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ci-failure-agent-service
                port:
                  number: 80
```

---

## Step 6: Verification & Testing

### 6.1 SSL/TLS Validation

```bash
# Test domain accessibility
curl -I https://ci-failure-agent.io

# Check certificate validity
echo | openssl s_client -servername ci-failure-agent.io \
  -connect ci-failure-agent.io:443 | grep -E "subject|issuer|Not Before|Not After"

# Test security headers
curl -I https://ci-failure-agent.io | grep -E "Strict-Transport|X-Frame|X-Content-Type"

# SSL Labs test
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=ci-failure-agent.io
```

### 6.2 HTTP to HTTPS Redirect

```bash
# Test redirect (should receive 301/302 to HTTPS)
curl -I http://ci-failure-agent.io

# Follow redirect
curl -L http://ci-failure-agent.io
```

### 6.3 Certificate Auto-Renewal

```bash
# Cert-manager automatically renews 30 days before expiration
# Monitor renewal events
kubectl get events --sort-by='.lastTimestamp' -n cert-manager

# View certificate details
kubectl describe certificate ci-failure-agent-tls
```

---

## Deliverables Checklist

- [ ] Custom domain registered
- [ ] DNS A records configured and propagated
- [ ] cert-manager installed on cluster
- [ ] Let's Encrypt ClusterIssuers configured
- [ ] TLS ingress deployed
- [ ] SSL certificate provisioned and active
- [ ] Security headers configured
- [ ] HTTPS endpoint verified working
- [ ] HTTP to HTTPS redirect tested
- [ ] SSL Labs score A or higher
- [ ] Certificate auto-renewal verified

---

## Troubleshooting

### Certificate Not Issued

```bash
# Check Certificate Request status
kubectl describe certificaterequest

# View cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check ingress annotations are correct
kubectl describe ingress ci-failure-agent-ingress
```

### DNS Resolution Issues

```bash
# Clear local DNS cache and test
flushall  # macOS
ipconfig /flushdns  # Windows

# Test with specific DNS server
nslookup ci-failure-agent.io 8.8.8.8
```

---

## Next Steps

→ **Phase 3**: Advanced Observability Setup (Starting Dec 30)

---

**Document Version**: 1.0
**Created**: December 14, 2025
**Owner**: DevOps/Infrastructure Team
