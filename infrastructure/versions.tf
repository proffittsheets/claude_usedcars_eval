terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Config supplied via backend.hcl (gitignored) — see backend.hcl.example
  backend "s3" {}
}
