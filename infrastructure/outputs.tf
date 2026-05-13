output "site_url" {
  description = "CloudFront HTTPS URL for the Car Vision Board site"
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "bucket_name" {
  description = "S3 bucket name — used for uploading site files"
  value       = aws_s3_bucket.site.bucket
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — needed to invalidate cache after deploys"
  value       = aws_cloudfront_distribution.site.id
}
