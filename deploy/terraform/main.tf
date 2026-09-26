# =============================================================================
# ByteSized Suite — AWS EKS Infrastructure Provisioning
# Terraform >= 1.5.0 | AWS Provider >= 5.0
#
# Provisions:
#   - VPC with 3 public + 3 private subnets across 3 AZs
#   - EKS cluster (Kubernetes 1.29) with managed node groups
#   - Node group: t3.medium × 2–10 nodes (auto-scaling)
#   - ECR repository for container images
#   - IAM roles and OIDC integration for pod-level AWS permissions
#   - ElastiCache Redis cluster (cache.t3.micro) for WebSocket pub/sub
#   - Application Load Balancer (via AWS Load Balancer Controller)
#   - Route53 DNS record pointing to ALB
#   - ACM certificate for TLS
#
# Usage:
#   terraform init
#   terraform plan -var="cluster_name=bytesized-prod"
#   terraform apply -var="cluster_name=bytesized-prod"
#   terraform destroy
#
# Outputs:
#   cluster_endpoint      — EKS API server endpoint
#   kubeconfig_command    — aws eks update-kubeconfig command
#   ecr_repository_url    — container registry URL
#   redis_endpoint        — ElastiCache Redis primary endpoint
#   alb_dns_name          — Application Load Balancer DNS name
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.20.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.10.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0.0"
    }
  }

  # Remote state backend (uncomment and configure for team usage)
  # backend "s3" {
  #   bucket         = "bytesized-terraform-state"
  #   key            = "prod/eks/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "bytesized-terraform-locks"
  # }
}

# ---------------------------------------------------------------------------
# PROVIDERS
# ---------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ByteSized"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "ByteSized Engineering Team"
      Repository  = "github.com/GAGAN7350/ByteSized"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# ---------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "bytesized-prod"
}

variable "environment" {
  description = "Deployment environment (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.29"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t3.medium"
}

variable "node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 10
}

variable "node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Root domain name for Route53 and ACM"
  type        = string
  default     = "bytesized.corp.example.com"
}

# ---------------------------------------------------------------------------
# DATA SOURCES
# ---------------------------------------------------------------------------

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

# ---------------------------------------------------------------------------
# LOCAL VALUES
# ---------------------------------------------------------------------------

locals {
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  account_id      = data.aws_caller_identity.current.account_id
  partition       = data.aws_partition.current.partition
  cluster_oidc_id = trimprefix(module.eks.cluster_oidc_issuer_url, "https://")

  private_subnets = [
    cidrsubnet(var.vpc_cidr, 4, 0),
    cidrsubnet(var.vpc_cidr, 4, 1),
    cidrsubnet(var.vpc_cidr, 4, 2),
  ]
  public_subnets = [
    cidrsubnet(var.vpc_cidr, 4, 8),
    cidrsubnet(var.vpc_cidr, 4, 9),
    cidrsubnet(var.vpc_cidr, 4, 10),
  ]
}

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------

resource "aws_vpc" "bytesized" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.cluster_name}-vpc"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

resource "aws_internet_gateway" "bytesized" {
  vpc_id = aws_vpc.bytesized.id
  tags   = { Name = "${var.cluster_name}-igw" }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.bytesized.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name = "${var.cluster_name}-private-${local.azs[count.index]}"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
    "kubernetes.io/role/internal-elb"           = "1"
  }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.bytesized.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-${local.azs[count.index]}"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
    "kubernetes.io/role/elb"                    = "1"
  }
}

resource "aws_eip" "nat" {
  count  = 3
  domain = "vpc"
  tags   = { Name = "${var.cluster_name}-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "bytesized" {
  count         = 3
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.cluster_name}-nat-${count.index}" }
  depends_on    = [aws_internet_gateway.bytesized]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.bytesized.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.bytesized.id
  }
  tags = { Name = "${var.cluster_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count  = 3
  vpc_id = aws_vpc.bytesized.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.bytesized[count.index].id
  }
  tags = { Name = "${var.cluster_name}-private-rt-${count.index}" }
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ---------------------------------------------------------------------------
# SECURITY GROUPS
# ---------------------------------------------------------------------------

resource "aws_security_group" "eks_nodes" {
  name        = "${var.cluster_name}-node-sg"
  description = "Security group for EKS worker nodes"
  vpc_id      = aws_vpc.bytesized.id

  ingress {
    description = "Allow all traffic within node security group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  ingress {
    description = "Allow HTTP from ALB"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.cluster_name}-node-sg" }
}

resource "aws_security_group" "redis" {
  name        = "${var.cluster_name}-redis-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.bytesized.id

  ingress {
    description     = "Allow Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.cluster_name}-redis-sg" }
}

# ---------------------------------------------------------------------------
# EKS CLUSTER (using simplified inline configuration)
# ---------------------------------------------------------------------------

resource "aws_iam_role" "eks_cluster" {
  name = "${var.cluster_name}-cluster-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_eks_cluster" "bytesized" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    security_group_ids      = [aws_security_group.eks_nodes.id]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  kubernetes_network_config {
    service_ipv4_cidr = "172.20.0.0/16"
    ip_family         = "ipv4"
  }

  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = aws_kms_key.eks.arn
    }
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]

  tags = { Name = var.cluster_name }
}

# KMS key for EKS secrets encryption
resource "aws_kms_key" "eks" {
  description             = "EKS Cluster Encryption Key — ${var.cluster_name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = { Name = "${var.cluster_name}-kms" }
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# OIDC Provider for pod-level IAM
resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.bytesized.identity[0].oidc[0].issuer
}

data "tls_certificate" "eks_oidc" {
  url = aws_eks_cluster.bytesized.identity[0].oidc[0].issuer
}

# ---------------------------------------------------------------------------
# EKS NODE GROUP
# ---------------------------------------------------------------------------

resource "aws_iam_role" "eks_nodes" {
  name = "${var.cluster_name}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_ecr_readonly" {
  policy_arn = "arn:${local.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_eks_node_group" "bytesized" {
  cluster_name    = aws_eks_cluster.bytesized.name
  node_group_name = "${var.cluster_name}-workers"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = [var.node_instance_type]
  ami_type        = "AL2_x86_64"
  capacity_type   = "ON_DEMAND"
  disk_size       = 50

  scaling_config {
    min_size     = var.node_min_size
    max_size     = var.node_max_size
    desired_size = var.node_desired_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role        = "worker"
    environment = var.environment
  }

  taint {
    key    = "bytesized.io/role"
    value  = "backend"
    effect = "NO_SCHEDULE"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_readonly,
  ]

  tags = { Name = "${var.cluster_name}-node-group" }
}

# ---------------------------------------------------------------------------
# ECR REPOSITORY
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "backend" {
  name                 = "bytesized/backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.eks.arn
  }

  tags = { Name = "bytesized-backend-ecr" }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 production images, expire untagged after 7 days"
      selection = {
        tagStatus      = "untagged"
        countType      = "sinceImagePushed"
        countUnit      = "days"
        countNumber    = 7
      }
      action = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------------------
# ELASTICACHE REDIS (for WebSocket pub/sub fan-out)
# ---------------------------------------------------------------------------

resource "aws_elasticache_subnet_group" "bytesized" {
  name       = "${var.cluster_name}-redis-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${var.cluster_name}-redis-subnet-group" }
}

resource "aws_elasticache_replication_group" "bytesized" {
  replication_group_id = "${var.cluster_name}-redis"
  description          = "ByteSized WebSocket pub/sub Redis cluster"

  node_type            = var.redis_node_type
  num_cache_clusters   = 2   # primary + 1 replica for HA
  port                 = 6379

  subnet_group_name    = aws_elasticache_subnet_group.bytesized.name
  security_group_ids   = [aws_security_group.redis.id]

  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true
  automatic_failover_enabled  = true
  multi_az_enabled             = true

  engine_version       = "7.2"
  parameter_group_name = "default.redis7"

  maintenance_window        = "sun:05:00-sun:06:00"
  snapshot_retention_limit  = 5
  snapshot_window           = "03:00-04:00"

  tags = { Name = "${var.cluster_name}-redis" }
}

# ---------------------------------------------------------------------------
# ACM CERTIFICATE
# ---------------------------------------------------------------------------

resource "aws_acm_certificate" "bytesized" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = "${var.cluster_name}-acm-cert" }
}

# ---------------------------------------------------------------------------
# HELM: NGINX Ingress Controller
# ---------------------------------------------------------------------------

resource "helm_release" "nginx_ingress" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  version          = "4.8.3"

  set {
    name  = "controller.replicaCount"
    value = "2"
  }
  set {
    name  = "controller.service.type"
    value = "LoadBalancer"
  }
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-type"
    value = "nlb"
  }
  set {
    name  = "controller.config.proxy-real-ip-cidr"
    value = "0.0.0.0/0"
  }

  depends_on = [aws_eks_node_group.bytesized]
}

# ---------------------------------------------------------------------------
# HELM: cert-manager
# ---------------------------------------------------------------------------

resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  namespace        = "cert-manager"
  create_namespace = true
  version          = "1.14.2"

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [aws_eks_node_group.bytesized]
}

# ---------------------------------------------------------------------------
# HELM: Prometheus Stack (kube-prometheus-stack)
# ---------------------------------------------------------------------------

resource "helm_release" "prometheus" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = "monitoring"
  create_namespace = true
  version          = "56.2.1"

  set {
    name  = "grafana.enabled"
    value = "true"
  }
  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "15d"
  }
  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage"
    value = "50Gi"
  }

  depends_on = [aws_eks_node_group.bytesized]
}

# ---------------------------------------------------------------------------
# KUBERNETES NAMESPACE
# ---------------------------------------------------------------------------

resource "kubernetes_namespace" "bytesized_prod" {
  metadata {
    name = "bytesized-prod"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "environment"                  = var.environment
    }
  }
  depends_on = [aws_eks_cluster.bytesized]
}

# ---------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------

output "cluster_endpoint" {
  description = "EKS cluster API server endpoint"
  value       = aws_eks_cluster.bytesized.endpoint
  sensitive   = false
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.bytesized.name
}

output "kubeconfig_command" {
  description = "Command to update local kubeconfig"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.bytesized.name} --region ${var.aws_region}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint address"
  value       = aws_elasticache_replication_group.bytesized.primary_endpoint_address
}

output "acm_certificate_arn" {
  description = "ARN of the ACM TLS certificate"
  value       = aws_acm_certificate.bytesized.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.bytesized.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}
