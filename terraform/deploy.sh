#!/bin/bash
# AWS EKS Cluster Deployment Script
# Automates Terraform deployment for CI/CD failure agent infrastructure
# Target domains: auditorsec.com, audityzer.com

set -e

echo "========================================"
echo "AWS EKS Cluster Deployment Script"
echo "========================================"
echo ""

# Configuration
AWS_REGION="us-east-1"
CLUSTER_NAME="ci-failure-agent-cluster"
TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    log_info "All prerequisites satisfied"
}

# Initialize Terraform
init_terraform() {
    log_info "Initializing Terraform..."
    cd "$TERRAFORM_DIR"
    terraform init
    log_info "Terraform initialized successfully"
}

# Validate Terraform configuration
validate_terraform() {
    log_info "Validating Terraform configuration..."
    terraform validate
    log_info "Terraform configuration is valid"
}

# Plan Terraform deployment
plan_terraform() {
    log_info "Planning Terraform deployment..."
    terraform plan -out=tfplan
    log_info "Terraform plan generated (tfplan)"
}

# Apply Terraform configuration
apply_terraform() {
    log_info "Applying Terraform configuration..."
    read -p "Do you want to continue with the deployment? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Deployment cancelled"
        exit 1
    fi
    
    terraform apply tfplan
    log_info "Infrastructure deployed successfully"
}

# Configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl..."
    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$CLUSTER_NAME"
    log_info "kubectl configured successfully"
}

# Verify cluster
verify_cluster() {
    log_info "Verifying EKS cluster..."
    kubectl get nodes
    log_info "Cluster verification complete"
}

# Install essential components
install_components() {
    log_info "Installing essential Kubernetes components..."
    
    # Install metrics-server
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    # Install Calico for network policies
    kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/tigera-operator.yaml
    
    log_info "Components installed successfully"
}

# Output information
output_info() {
    log_info "Deployment Summary:"
    echo "Cluster Name: $CLUSTER_NAME"
    echo "Region: $AWS_REGION"
    echo "Domains: auditorsec.com, audityzer.com"
    echo ""
    echo "Next steps:"
    echo "1. Deploy CI/CD failure agent application"
    echo "2. Configure domain DNS records"
    echo "3. Install TLS certificates"
    echo "4. Deploy monitoring and logging solutions"
}

# Cleanup function
cleanup() {
    log_info "Cleanup function called"
    if [ -f "$TERRAFORM_DIR/tfplan" ]; then
        rm "$TERRAFORM_DIR/tfplan"
    fi
}

# Main execution
main() {
    log_info "Starting EKS cluster deployment process..."
    
    check_prerequisites
    init_terraform
    validate_terraform
    plan_terraform
    apply_terraform
    configure_kubectl
    verify_cluster
    install_components
    output_info
    
    log_info "Deployment process completed successfully!"
}

# Trap errors
trap cleanup EXIT

# Execute main function
main "$@"
