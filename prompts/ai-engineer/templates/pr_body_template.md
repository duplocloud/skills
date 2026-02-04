## Summary
- Added encrypted S3 app logs bucket (SSE-KMS, 30-day lifecycle, public access block)
- Wired into dev environment
- Added PR CI workflow for terraform fmt/validate/plan

## Repo map (discovered)
- Terraform root(s):
- Modules dir:
- Dev env entrypoint:
- CI workflows:

## Changes
- Added:
- Modified:

## Validation
- terraform fmt: ✅/❌
- terraform init -backend=false: ✅/❌
- terraform validate: ✅/❌
- terraform plan (best-effort): ✅/⚠️ (explain)

## Notes / assumptions
-

## Rollback
Revert this PR or remove:
- <files/modules>