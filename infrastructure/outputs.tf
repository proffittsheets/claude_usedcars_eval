output "cloudfront_url" {
  description = "HTTPS URL for the Car Vision Board site"
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — needed to invalidate cache after deploys"
  value       = aws_cloudfront_distribution.site.id
}

output "s3_bucket_name" {
  description = "S3 bucket name — used for uploading site files"
  value       = aws_s3_bucket.site.bucket
}

output "s3_sync_command" {
  description = "Command to upload the built site to S3"
  value       = "aws s3 sync site/ s3://${aws_s3_bucket.site.bucket}/ --delete --profile ${var.aws_profile}"
}

output "cloudfront_invalidate_command" {
  description = "Command to clear CloudFront cache after uploading new files"
  value       = "aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.site.id} --paths '/*' --profile ${var.aws_profile}"
}
