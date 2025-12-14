# Phase 2: Custom Domain & SSL/TLS Configuration
## Secure HTTPS Setup with cert-manager

### Step 1: Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager CRDs
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.crds.yaml

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0

# Verify installation
kubectl get pods --namespace cert-manager
```

### Step 2: Create Let's Encrypt Issuer

```yaml
# Save as: cert-issuer.yaml
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
          class: nginx
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
          class: nginx
```

```bash
# Apply issuers
kubectl apply -f cert-issuer.yaml

# Verify
kubectl get clusterissuers
```

### Step 3: Configure Ingress with TLS

```yaml
# Update ingress-tls.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ci-failure-agent-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.2 TLSv1.3"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.anti-corruption-agent.tech
    - anti-corruption-agent.tech
    secretName: anti-corruption-agent-tls
  rules:
  - host: anti-corruption-agent.tech
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ci-failure-agent
            port:
              number: 80
  - host: api.anti-corruption-agent.tech
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ci-failure-agent
            port:
              number: 80
```

```bash
# Apply ingress
kubectl apply -f ingress-tls.yaml

# Check certificate status
kubectl describe certificate anti-corruption-agent-tls -n production
```

### Step 4: DNS Configuration

1. **Register Domain**
   - Register your domain (e.g., anti-corruption-agent.tech)
   - Use a registrar like AWS Route 53, GoDaddy, or Namecheap

2. **Get Load Balancer IP**
   ```bash
   # Get ELB/LoadBalancer IP
   kubectl get svc -n ingress-nginx
   # Note the EXTERNAL-IP
   ```

3. **Update DNS Records**
   - Create A record: `anti-corruption-agent.tech` → `<EXTERNAL-IP>`
   - Create CNAME: `api.anti-corruption-agent.tech` → `anti-corruption-agent.tech`
   - Wait for DNS propagation (can take up to 24 hours)

4. **Verify DNS**
   ```bash
   nslookup anti-corruption-agent.tech
   ```

### Step 5: Security Headers Configuration

```yaml
# Add to Ingress annotations
metadata:
  annotations:
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
      more_set_headers "Permissions-Policy: geolocation=(), microphone=(), camera=()";
```

### Verification Checklist

- [ ] cert-manager installed and running
- [ ] ClusterIssuers created (prod and staging)
- [ ] Ingress configured with TLS annotation
- [ ] Certificate issued (check: `kubectl get certificate -n production`)
- [ ] Domain registered and DNS configured
- [ ] DNS records propagated
- [ ] HTTPS accessible via browser
- [ ] Security headers configured
- [ ] SSL A+ rating from SSL Labs

### Troubleshooting

**Certificate not issuing:**
```bash
kubectl describe certificaterequest -n production
kubectl logs -n cert-manager deployment/cert-manager
```

**DNS not resolving:**
```bash
dig anti-corruption-agent.tech
nslookup anti-corruption-agent.tech
```

**Ingress not working:**
```bash
kubectl describe ingress ci-failure-agent-ingress -n production
kubectl get ingress -n production
```
