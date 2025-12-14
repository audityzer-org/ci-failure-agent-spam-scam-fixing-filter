# Phase 2: Domain & SSL/TLS Configuration

## Timeline
**Start Date**: December 23, 2025
**End Date**: December 27, 2025
**Duration**: 5 days (1 week)

## Overview
Phase 2 focuses on securing the CI Failure Agent platform with a custom domain and SSL/TLS encryption using Let's Encrypt and cert-manager on Kubernetes.

---

## Step 1: Domain Registration & Selection

### Decision: Select Custom Domain

**Recommended Domain**: `anti-corruption-agent.tech`

Alternatives:
- `ci-agent.io`
- `failure-analyzer.cloud`
- `audit-intelligence.ai`

### Domain Registration Process

#### Option A: Register with AWS Route 53
```bash
# Using AWS CLI to register domain
aws route53domains register-domain \
  --domain-name anti-corruption-agent.tech \
  --duration-in-years 1 \
  --auto-renew \
  --privacy-protection-enabled
```

#### Option B: Register with Third-Party Provider
- **Namecheap**: https://www.namecheap.com
- **GoDaddy**: https://www.godaddy.com
- **Google Domains**: https://domains.google

**Estimated Cost**: $10-15 per year

---

## Step 2: DNS Configuration

### Create DNS Records in Route 53

```bash
# Set up hosted zone
aws route53 create-hosted-zone \
  --name anti-corruption-agent.tech \
  --caller-reference $(date +%s)

# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name anti-corruption-agent.tech \
  --query 'HostedZones[0].Id' --output text)
```

### Add A Record (Points to Load Balancer)

```bash
# Get load balancer IP from Kubernetes
LOAD_BALANCER_IP=$(kubectl get svc ci-failure-agent-service \
  -n ci-failure-agent \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "anti-corruption-agent.tech",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'$LOAD_BALANCER_IP'"}]
        }
      }
    ]
  }'
```

### Add CNAME Record for API Subdomain

```bash
# Create CNAME record for api subdomain
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.anti-corruption-agent.tech",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "anti-corruption-agent.tech"}]
        }
      }
    ]
  }'
```

### DNS Verification

```bash
# Verify DNS propagation
nslookup anti-corruption-agent.tech
dig anti-corruption-agent.tech
dig api.anti-corruption-agent.tech

# Using online tool
http://whatsmydns.net/
```

---

## Step 3: SSL/TLS Certificate Management with cert-manager

### Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Verify installation
kubectl get pods --namespace cert-manager
```

### Create ClusterIssuer for Let's Encrypt

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@anti-corruption-agent.tech
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: aws-load-balancer
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@anti-corruption-agent.tech
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: aws-load-balancer
EOF
```

### Update Ingress for HTTPS

```bash
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-ingress
  namespace: ci-failure-agent
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: aws-load-balancer
  tls:
  - hosts:
    - anti-corruption-agent.tech
    - api.anti-corruption-agent.tech
    secretName: anti-corruption-tls
  rules:
  - host: anti-corruption-agent.tech
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ci-failure-agent-service
            port:
              number: 80
  - host: api.anti-corruption-agent.tech
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ci-failure-agent-service
            port:
              number: 80
EOF
```

### Verify Certificate Creation

```bash
# Check certificate status
kubectl get certificate -n ci-failure-agent
kubectl describe certificate anti-corruption-tls -n ci-failure-agent

# Check TLS secret
kubectl get secret anti-corruption-tls -n ci-failure-agent -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

---

## Step 4: Security Headers Configuration

### Add Security Headers to Ingress

```bash
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-ingress
  namespace: ci-failure-agent
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://anti-corruption-agent.tech"
    # Security headers
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Content-Security-Policy: default-src 'self'";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
spec:
  # ... rest of ingress config
EOF
```

---

## Step 5: Subdomain Management

### API Subdomain
```bash
# api.anti-corruption-agent.tech
# Routes to: /api/* paths
```

### Documentation Subdomain (Optional)
```bash
# docs.anti-corruption-agent.tech
# Routes to: Swagger/OpenAPI documentation
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "docs.anti-corruption-agent.tech",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "anti-corruption-agent.tech"}]
        }
      }
    ]
  }'
```

---

## Step 6: HTTPS Testing & Validation

### Test HTTPS Connection

```bash
# Test with curl
curl -v https://anti-corruption-agent.tech/health
curl -v https://api.anti-corruption-agent.tech/health

# Check SSL certificate
echo | openssl s_client -servername anti-corruption-agent.tech \
  -connect anti-corruption-agent.tech:443

# Online SSL checker
# https://www.ssllabs.com/ssltest/
```

### Verify Security Headers

```bash
# Check response headers
curl -I https://anti-corruption-agent.tech

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Content-Security-Policy: default-src 'self'
```

---

## Troubleshooting

### Certificate Not Issuing

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
kubectl logs -n cert-manager deployment/cert-manager-webhook

# Check certificate request status
kubectl describe certificaterequest -n ci-failure-agent
kubectl describe order -n ci-failure-agent
kubectl describe challenge -n ci-failure-agent
```

### DNS Not Resolving

```bash
# Flush DNS cache
sudo systemctl restart systemd-resolved

# Check nameservers
dig NS anti-corruption-agent.tech

# Verify Route 53 configuration
aws route53 get-hosted-zone --id $HOSTED_ZONE_ID
aws route53 list-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID
```

---

## Success Criteria

- ✅ Custom domain registered and active
- ✅ DNS records properly configured
- ✅ cert-manager installed on cluster
- ✅ Let's Encrypt certificate issued and valid
- ✅ HTTPS working on domain and subdomains
- ✅ Security headers present in all responses
- ✅ SSL Labs rating: A or higher
- ✅ No browser warnings for certificate

---

## Cost Estimation

| Item | Cost | Duration |
|------|------|----------|
| Domain Registration | $10-15 | 1 year |
| SSL/TLS Certificate | FREE (Let's Encrypt) | 90 days (auto-renew) |
| **Total** | **~$12** | **1 year** |

---

## Next Phase
Once domain and SSL/TLS are configured, proceed to **Phase 3: Advanced Observability Stack** (December 23 - January 3, 2025)

---

**Document Version**: 1.0
**Last Updated**: December 14, 2025, 11:00 AM EET
**Status**: Ready for Implementation
**Owner**: DevOps/Security Team
