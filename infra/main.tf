# Minimal AWS deployment for the Flask backend: a private S3 bucket for user uploads, the IAM role
# the app runs as (EC2 host running docker-compose), and an inline role policy that lets the app
# read and write objects in that bucket and nothing else.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region for the deployment"
  type        = string
  default     = "us-east-2"
}

variable "uploads_bucket_name" {
  description = "Globally unique name of the user-uploads bucket"
  type        = string
  default     = "flask-backend-user-uploads"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "user_uploads" {
  bucket = var.uploads_bucket_name

  tags = {
    app     = "flask-backend"
    purpose = "user uploads"
  }
}

resource "aws_s3_bucket_public_access_block" "user_uploads" {
  bucket = aws_s3_bucket.user_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "app" {
  name = "flask-backend-app"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "flask-backend-app"
  role = aws_iam_role.app.name
}

resource "aws_iam_role_policy" "app_user_uploads" {
  name = "flask-backend-user-uploads"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "UserUploadsObjectReadWrite"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.user_uploads.arn}/*"
      }
    ]
  })
}

output "uploads_bucket" {
  value = aws_s3_bucket.user_uploads.bucket
}

output "app_role_arn" {
  value = aws_iam_role.app.arn
}
