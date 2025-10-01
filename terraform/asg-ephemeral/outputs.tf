output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.ephemeral.name
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.ephemeral.id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = var.create_alb ? aws_lb.main[0].dns_name : null
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = var.create_alb ? aws_lb.main[0].arn : null
}

output "cloudwatch_log_group" {
  description = "CloudWatch Log Group name for /var/log/messages"
  value       = "${var.asg_name}-messages"
}