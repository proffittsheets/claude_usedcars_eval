variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile name to use for authentication"
  type        = string
  default     = "default"
}

variable "bucket_name" {
  description = "S3 bucket name — must be globally unique across all AWS accounts"
  type        = string
}

variable "price_class" {
  description = "CloudFront price class. PriceClass_100 = US/Europe only (cheapest). PriceClass_All = worldwide."
  type        = string
  default     = "PriceClass_100"
}
