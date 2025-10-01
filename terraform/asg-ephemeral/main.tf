# Get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# IAM Role for EC2 instances
resource "aws_iam_role" "ec2_role" {
  name = "${var.asg_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for SSM Session Manager
resource "aws_iam_role_policy_attachment" "ssm_managed_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.ec2_role.name
}

# IAM Policy for CloudWatch Logs
resource "aws_iam_role_policy_attachment" "cloudwatch_logs_policy" {
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = aws_iam_role.ec2_role.name
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.asg_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# Security Group for EC2 instances
resource "aws_security_group" "ec2_sg" {
  name        = "${var.asg_name}-ec2-sg"
  description = "Security group for EC2 instances"
  vpc_id      = var.vpc_id

  # Allow HTTP from ALB (will be referenced if ALB is created)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Will be restricted by ALB SG if created
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.asg_name}-ec2-sg"
  }
}

# Launch Template
resource "aws_launch_template" "ephemeral" {
  name          = "${var.asg_name}-launch-template"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = "t3.micro" # Adjust as needed
  user_data     = base64encode(templatefile("${path.module}/user_data.sh", { asg_name = var.asg_name }))

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_profile.name
  }

  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.asg_name}-instance"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name = "${var.asg_name}-volume"
    }
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "ephemeral" {
  name                = var.asg_name
  launch_template {
    id      = aws_launch_template.ephemeral.id
    version = "$Latest"
  }

  vpc_zone_identifier = var.private_subnets
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1

  # Replace instances every 30 days (30 * 24 * 3600 = 2,592,000 seconds)
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  # Force replacement every 30 days using lifecycle
  lifecycle {
    create_before_destroy = true
  }

  # Tag instances
  tag {
    key                 = "Name"
    value               = "${var.asg_name}-instance"
    propagate_at_launch = true
  }

  # Schedule instance refresh every 30 days
  dynamic "scheduled_action" {
    for_each = var.create_alb ? [] : [1] # Only create if not using ALB health checks
    content {
      name             = "${var.asg_name}-refresh"
      min_size         = 1
      max_size         = 3
      desired_capacity = 1
      recurrence       = "0 0 */30 * *" # Every 30 days at midnight UTC
    }
  }
}

# Bonus: Application Load Balancer
resource "aws_lb" "main" {
  count = var.create_alb ? 1 : 0

  name               = var.asg_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg[0].id]
  subnets            = var.public_subnets

  tags = {
    Name = var.asg_name
  }
}

resource "aws_security_group" "alb_sg" {
  count = var.create_alb ? 1 : 0

  name        = "${var.asg_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.asg_name}-alb-sg"
  }
}

resource "aws_lb_target_group" "http" {
  count = var.create_alb ? 1 : 0

  name        = "${var.asg_name}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    path                = "/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200-399"
  }
}

resource "aws_lb_listener" "https" {
  count = var.create_alb && var.certificate_arn != null ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.http[0].arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count = var.create_alb ? 1 : 0

  load_balancer_arn = aws_lb.main[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Attach ASG to target group if ALB is created
resource "aws_autoscaling_attachment" "asg_alb" {
  count = var.create_alb ? 1 : 0

  autoscaling_group_name = aws_autoscaling_group.ephemeral.name
  lb_target_group_arn    = aws_lb_target_group.http[0].arn
}