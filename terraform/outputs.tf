# Terraform Outputs for CI Failure Agent Production Deployment

output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_version" {
  description = "EKS cluster version"
  value       = aws_eks_cluster.main.version
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ips" {
  description = "Elastic IPs of NAT gateways"
  value       = aws_eip.nat[*].public_ip
}

output "worker_node_autoscaling_group_names" {
  description = "Names of the Auto Scaling Groups for worker nodes"
  value       = aws_autoscaling_group.main[*].name
}

output "worker_node_security_group_id" {
  description = "Security group ID for worker nodes"
  value       = aws_security_group.worker_nodes.id
}

output "rds_cluster_endpoint" {
  description = "RDS cluster write endpoint"
  value       = aws_rds_cluster.main.endpoint
  sensitive   = true
}

output "rds_reader_endpoint" {
  description = "RDS cluster read endpoint for read-only replicas"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_rds_cluster.main.database_name
}

output "rds_master_username" {
  description = "RDS database master username"
  value       = aws_rds_cluster.main.master_username
  sensitive   = true
}

output "rds_cluster_port" {
  description = "RDS cluster port"
  value       = aws_rds_cluster.main.port
}

output "rds_cluster_resource_id" {
  description = "RDS cluster resource ID"
  value       = aws_rds_cluster.main.cluster_resource_id
}

output "iam_role_arn" {
  description = "ARN of the EKS service role"
  value       = aws_iam_role.eks_service_role.arn
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile for worker nodes"
  value       = aws_iam_instance_profile.worker_nodes.name
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for EKS cluster logs"
  value       = aws_cloudwatch_log_group.eks.name
}

output "kubeconfig_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "deployment_status" {
  description = "Deployment completion status"
  value       = "Production-ready infrastructure successfully deployed"
}

output "access_instructions" {
  description = "Instructions to access the cluster"
  value       = "Configure kubectl: aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.aws_region}"
}

output "monitoring_dashboard_url" {
  description = "URL to CloudWatch monitoring dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}"
}

output "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  value       = "s3://${aws_s3_bucket.terraform_state.id}"
  sensitive   = true
}

output "deployment_summary" {
  description = "Complete deployment summary"
  value = {
    cluster_name  = aws_eks_cluster.main.name
    region        = var.aws_region
    database_host = aws_rds_cluster.main.endpoint
    node_count    = var.desired_size
  }
}
