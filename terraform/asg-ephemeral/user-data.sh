# user_data.tftpl
#!/bin/bash
set -e

# Update system
dnf update -y

# Install Nginx
dnf install -y nginx

# Configure Nginx
cat > /etc/nginx/conf.d/default.conf << 'EOF'
${nginx_config}
EOF

# Start and enable Nginx
systemctl enable nginx --now

# Install CloudWatch Logs agent
dnf install -y amazon-cloudwatch-agent

# Configure CloudWatch Logs
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "agent": {
    "metrics_collection_interval": 60,
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "${log_group_name}",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    },
    "force_flush_interval": 15
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Ensure SSM agent is running
systemctl enable amazon-ssm-agent --now