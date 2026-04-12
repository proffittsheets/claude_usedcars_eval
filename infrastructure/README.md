# Infrastructure — Car Vision Board

Terraform configuration for hosting the Car Vision Board static site on AWS using S3 + CloudFront.

**Architecture:** S3 bucket (private) → CloudFront distribution with Origin Access Control → `https://xxxx.cloudfront.net`

No custom domain, no ACM certificate, no Route53 required.

---

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.6
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with a local profile (`aws configure`)
- An AWS account with permissions to create S3 buckets, CloudFront distributions, and IAM policies

---

## First-Time Setup

**1. Create your local variables file**

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region  = "us-east-1"
aws_profile = "default"                   # your AWS CLI profile name
bucket_name = "sheets-car-vision-board"   # must be globally unique — change if already taken
```

`terraform.tfvars` is gitignored and never committed.

**2. Initialize Terraform**

```bash
terraform init
```

This downloads the AWS provider. Only needed once (or after provider version changes).

**3. Preview the changes**

```bash
terraform plan
```

Review what will be created: 1 S3 bucket, 1 CloudFront distribution, 1 OAC, 1 bucket policy.

**4. Apply**

```bash
terraform apply
```

Type `yes` when prompted. Takes ~5 minutes — CloudFront distributions take time to propagate globally.

**5. Note your outputs**

After apply completes, Terraform prints:

```
cloudfront_url                = "https://xxxx.cloudfront.net"
cloudfront_distribution_id    = "EXXXXXXXXXXXX"
s3_bucket_name                = "sheets-car-vision-board"
s3_sync_command               = "aws s3 sync site/ s3://sheets-car-vision-board/ --delete --profile default"
cloudfront_invalidate_command = "aws cloudfront create-invalidation --distribution-id EXXXXXXXXXXXX --paths '/*' --profile default"
```

Save the `s3_sync_command` and `cloudfront_invalidate_command` — you'll use them every time you deploy.

You can re-print outputs at any time with:

```bash
terraform output
```

---

## Deploying the Site

Run these from the **root of the repo** (not the `infrastructure/` folder) after building the site with `python3 build.py`:

**1. Build the site**

```bash
python3 build.py
```

**2. Upload to S3**

```bash
aws s3 sync site/ s3://YOUR-BUCKET-NAME/ --delete --profile YOUR-PROFILE
```

The `--delete` flag removes files from S3 that no longer exist locally (e.g. a car page that was removed).

**3. Invalidate CloudFront cache**

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR-DISTRIBUTION-ID \
  --paths '/*' \
  --profile YOUR-PROFILE
```

This forces CloudFront to fetch fresh files from S3. Without it, visitors may see cached old content for up to 1 hour (HTML) or 7 days (images).

> Tip: copy the exact commands from `terraform output` — they already have your bucket name, distribution ID, and profile filled in.

---

## Cache Behavior

| Content | TTL | Notes |
|---|---|---|
| HTML pages (`*.html`) | 1 hour | Short TTL so updates propagate quickly |
| Static assets (`/static/`) | 24 hours | CSS, JS, fonts |
| Car images (`/data/raw/images/`) | 7 days | Images rarely change |

A cache invalidation (`/*`) clears everything immediately regardless of TTL.

---

## Making Infrastructure Changes

Edit the `.tf` files, then:

```bash
terraform plan   # preview
terraform apply  # apply
```

Terraform only changes what differs — it won't recreate the bucket or distribution unless necessary.

---

## Tearing Down

To delete all AWS resources created by this config:

```bash
terraform destroy
```

> Note: the S3 bucket must be empty before it can be deleted. If `destroy` fails on the bucket, empty it first:
> ```bash
> aws s3 rm s3://YOUR-BUCKET-NAME --recursive --profile YOUR-PROFILE
> ```
> Then re-run `terraform destroy`.

---

## File Reference

| File | Purpose |
|---|---|
| `main.tf` | S3 bucket, CloudFront distribution, OAC, and bucket policy |
| `variables.tf` | Variable declarations and defaults |
| `outputs.tf` | CloudFront URL and deploy commands |
| `terraform.tfvars.example` | Template — commit this, not `terraform.tfvars` |
| `terraform.tfvars` | Your local values — **gitignored, never commit** |
