#!/usr/bin/env bash
# Removes the demo citizen's applications so each demo take starts clean.
set -euo pipefail
R=us-west-2
TABLE=$(aws ssm get-parameter --name /app/workshop/govease/applications-table --region $R --no-cli-pager --query Parameter.Value --output text)
IDS=$(aws dynamodb scan --table-name "$TABLE" --region $R --no-cli-pager --filter-expression "citizen_id = :c" --expression-attribute-values '{":c":{"S":"CIT-03"}}' --query 'Items[].application_id.S' --output text)
for id in $IDS; do
  aws dynamodb delete-item --table-name "$TABLE" --region $R --no-cli-pager --key "{\"application_id\":{\"S\":\"$id\"}}"
  echo "deleted $id"
done
echo "Demo reset complete."
