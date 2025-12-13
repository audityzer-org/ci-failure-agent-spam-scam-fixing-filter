#!/bin/bash
# Production Deployment Script for CI/CD Failure Agent
# Supports: AWS EKS, Google GKE, Azure AKS

set -e

echo "=== CI/CD Failure Agent - Production Deployment ==="

# Configuration
NAMESPACE="production"
MONITORING_NS="monitoring"
APP_NAME="ci-failure-agent"
REGION=${REGION:-us-east-1}
CLUSTER_NAME=${CLUSTER_NAME:-ci-failure-agent}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    command -v kubectl >/dev/null 2>&1 || print_error "kubectl is not installed"
    command -v helm >/dev/null 2>&1 || print_warning "helm is not installed (optional)"
    
    kubectl cluster-info >/dev/null 2>&1 || print_error "Cannot connect to Kubernetes cluster"
    
    print_status "All prerequisites met"
}

# Create namespaces
create_namespaces() {
    print_status "Creating Kubernetes namespaces..."
    
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace $MONITORING_NS --dry-run=client -o yaml | kubectl apply -f -
    
    print_status "Namespaces created successfully"
}

# Create secrets
create_secrets() {
    print_status "Creating Kubernetes secrets..."
    
    read -sp "Enter Database URL: " DATABASE_URL
    echo
    read -sp "Enter Google API Key: " GOOGLE_API_KEY
    echo
    
    kubectl create secret generic app-secrets \
        --from-literal=database-url="$DATABASE_URL" \
        --from-literal=google-api-key="$GOOGLE_API_KEY" \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_status "Secrets created successfully"
}

# Deploy Kubernetes manifests
deploy_manifests() {
    print_status "Deploying Kubernetes manifests..."
    
    cd k8s
    
    kubectl apply -f deployment.yaml -n $NAMESPACE
    print_status "Deployment applied"
    
    kubectl apply -f service.yaml -n $NAMESPACE
    print_status "Services applied"
    
    kubectl apply -f ingress-storage-monitoring.yaml
    print_status "Ingress, storage, and monitoring applied"
    
    cd ..
}

# Wait for deployment
wait_for_deployment() {
    print_status "Waiting for deployment to be ready..."
    
    kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=5m
    
    print_status "Deployment is ready"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    print_status "Checking pods..."
    kubectl get pods -n $NAMESPACE
    
    print_status "Checking services..."
    kubectl get svc -n $NAMESPACE
    
    print_status "Checking ingress..."
    kubectl get ingress
    
    # Get service endpoint
    ENDPOINT=$(kubectl get svc $APP_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    if [ "$ENDPOINT" != "pending" ]; then
        print_status "Service is accessible at: http://$ENDPOINT"
    else
        print_warning "LoadBalancer IP is still pending. Check again later."
    fi
}

# Main execution
main() {
    print_status "Starting production deployment..."
    
    check_prerequisites
    create_namespaces
    create_secrets
    deploy_manifests
    wait_for_deployment
    verify_deployment
    
    print_status "=== Deployment completed successfully ==="
    print_status "Next steps:"
    echo "  1. Configure DNS for your ingress domain"
    echo "  2. Set up SSL/TLS certificates"
    echo "  3. Configure backup policies"
    echo "  4. Set up monitoring alerts"
    echo "  5. Schedule regular backups"
}

main "$@"
