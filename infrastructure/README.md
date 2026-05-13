# Infrastructure — Car Vision Board

AWS infrastructure for the Car Vision Board static site, managed with Terraform.

**What's provisioned:**
- S3 bucket (private, no public access)
- CloudFront distribution (HTTPS, serves from S3 via Origin Access Control)
- Bucket policy allowing only this CloudFront distribution to read from S3

No custom domain, no ACM certificate, no Route53 required.

---

## What is and isn't in git

This repo is public. Nothing in the committed files contains credentials, account IDs, bucket names, or any value specific to your AWS account.

### Committed (safe to be public)

| File | What it contains |
|------|-----------------|
| `versions.tf` | Terraform version constraints, provider requirements, and backend type |
| `variables.tf` | Variable declarations — names and types only, no values |
| `main.tf` | All resource definitions |
| `outputs.tf` | Output definitions — site URL, bucket name, distribution ID |
| `backend.hcl.example` | Template showing the shape of the backend config |
| `terraform.tfvars.example` | Template showing which variables need values |
| `deploy.sh` | Script to build, sync files to S3, and invalidate the CloudFront cache |

### Gitignored (never committed)

| File/pattern | Why |
|-------------|-----|
| `backend.hcl` | Contains your state bucket name, region, and lock settings |
| `terraform.tfvars` | Contains your site bucket name and other config specific to your account |
| `.terraform/` | Provider binaries downloaded on init |
| `.terraform.lock.hcl` | Lock file generated on init |
| `terraform.tfstate`, `terraform.tfstate.backup` | State files — stored remotely in S3, never locally |

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.10
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with a local profile (`aws configure`)
- An AWS account with permissions to create S3, CloudFront, and IAM resources

Terraform uses the standard AWS credential chain — it picks up `~/.aws/credentials` or the named profile in your `terraform.tfvars`. No credentials go in any file.

---

## One-time bootstrap

Terraform stores its state in S3, using S3's native conditional writes for locking (requires Terraform >= 1.10 — no DynamoDB table needed). The bucket must exist before you can run `terraform init`. Create it once manually:

```bash
# Create the state bucket (pick any unique name)
aws s3api create-bucket \
  --bucket your-tf-state-bucket \
  --region us-east-1

# Enable versioning so you can recover from accidental state corruption
aws s3api put-bucket-versioning \
  --bucket your-tf-state-bucket \
  --versioning-configuration Status=Enabled
```

---

## First-time setup

1. **Create your backend config** (gitignored):
   ```bash
   cd infrastructure
   cp backend.hcl.example backend.hcl
   # Edit backend.hcl with your state bucket name
   ```

2. **Create your variables file** (gitignored):
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your site bucket name and AWS profile
   ```

3. **Initialize Terraform:**
   ```bash
   terraform init -backend-config=backend.hcl
   ```

4. **Preview what will be created:**
   ```bash
   terraform plan
   ```

5. **Apply:**
   ```bash
   terraform apply
   ```

After apply, Terraform prints the CloudFront URL. Takes ~5 minutes — CloudFront distributions take time to propagate globally.

---

## Deploying the site

From the `infrastructure/` folder, run:

```bash
./deploy.sh
```

The script builds the site, syncs files to S3, and invalidates the CloudFront cache. It reads the bucket name and distribution ID from Terraform outputs — no hardcoded values.

A CloudFront invalidation typically propagates within 1–2 minutes.

---

## Cache behavior

| Content | TTL | Notes |
|---|---|---|
| HTML pages (`*.html`) | 1 hour | Short TTL so updates propagate quickly |
| Static assets (`/static/`) | 24 hours | CSS, JS, fonts |
| Car images (`/data/raw/images/`) | 7 days | Images rarely change |

A cache invalidation (`/*`) clears everything immediately regardless of TTL.

---

## Day-to-day workflow

```bash
# See what would change
terraform plan

# Apply changes
terraform apply

# Deploy the site (build + upload + cache invalidation)
./deploy.sh
```

---

## Tearing down

```bash
terraform destroy
```

> **Note:** The S3 bucket must be empty before it can be deleted. If `destroy` fails on the bucket, empty it first:
> ```bash
> aws s3 rm s3://$(terraform output -raw bucket_name) --recursive
> ```
> Then re-run `terraform destroy`.
