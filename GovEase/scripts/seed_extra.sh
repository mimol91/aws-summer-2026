#!/usr/bin/env bash
# Adds the demo citizen's documents and the tax clearance service that the seed kit lacks.
set -euo pipefail
R=us-west-2
BUCKET=$(aws ssm get-parameter --name /app/workshop/govease/documents-bucket --region $R --no-cli-pager --query Parameter.Value --output text)
SERVICES=$(aws ssm get-parameter --name /app/workshop/govease/services-table --region $R --no-cli-pager --query Parameter.Value --output text)

aws s3 sync data/samples "s3://$BUCKET/citizens/CIT-03/" --region $R --no-cli-pager

aws dynamodb put-item --table-name "$SERVICES" --region $R --no-cli-pager --item '{
  "service_id": {"S": "SVC-TAX-CLEARANCE"},
  "name": {"S": "Tax clearance certificate"},
  "department": {"S": "Tax Authority"},
  "required_documents": {"S": "national_id, existing_license"},
  "fee": {"N": "0"},
  "timeline_days": {"N": "2"}
}'
echo "Seeded documents for CIT-03 and SVC-TAX-CLEARANCE service."
