variable "asg_name" {
  description = "Name of the Auto Scaling Group"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ASG will be deployed"
  type        = string
}

variable "private_subnets" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "load_balancer_url" {
  description = "Load balancer URL (for health checks if needed)"
  type        = string
  default     = ""
}

# Bonus variables for ALB
variable "create_alb" {
  description = "Whether to create an Application Load Balancer"
  type        = bool
  default     = false
}

variable "public_subnets" {
  description = "List of public subnet IDs (required if create_alb is true)"
  type        = list(string)
  default     = []
}

variable "certificate_arn" {
  description = "ARN of the SSL certificate for HTTPS listener"
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Domain name for the ALB (optional)"
  type        = string
  default     = null
}