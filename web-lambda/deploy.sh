#!/usr/bin/env bash
# Deploys the hosted web UI as a Lambda with a public function URL (sign-in still required via Cognito).
set -euo pipefail
cd "$(dirname "$0")"
R=us-west-2; ACC=$(aws sts get-caller-identity --query Account --output text --no-cli-pager)
FN=AgentCore-govease-web; ROLE=AgentCore-govease-web
RUNTIME_ARN=$(grep -oE 'arn:aws:bedrock-agentcore:[^"'"'"' ]+:runtime/[A-Za-z0-9_-]+' ../GovEase/app/GovEaseAgent/.bedrock_agentcore.yaml | head -1)
CLIENT_ID=$(python3 -c "import json;print(json.load(open('../GovEase/cognito_config.json'))['web_client_id'])")
TRUST='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam get-role --role-name $ROLE --no-cli-pager >/dev/null 2>&1 || { aws iam create-role --role-name $ROLE --assume-role-policy-document "$TRUST" --no-cli-pager >/dev/null; sleep 10; }
aws iam put-role-policy --role-name $ROLE --policy-name govease-web --no-cli-pager --policy-document '{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"},
 {"Effect":"Allow","Action":["bedrock-agentcore:InvokeAgentRuntime"],"Resource":"*"}]}'
rm -f web.zip && zip -q web.zip handler.py index.html
ENV="Variables={RUNTIME_ARN=$RUNTIME_ARN,COGNITO_CLIENT_ID=$CLIENT_ID}"
if aws lambda get-function --function-name $FN --region $R --no-cli-pager >/dev/null 2>&1; then
  aws lambda update-function-code --function-name $FN --zip-file fileb://web.zip --region $R --no-cli-pager >/dev/null
  aws lambda wait function-updated-v2 --function-name $FN --region $R
  aws lambda update-function-configuration --function-name $FN --environment "$ENV" --timeout 300 --region $R --no-cli-pager >/dev/null
else
  aws lambda create-function --function-name $FN --runtime python3.12 --handler handler.handler --role arn:aws:iam::$ACC:role/$ROLE --timeout 300 --memory-size 512 --environment "$ENV" --zip-file fileb://web.zip --region $R --no-cli-pager >/dev/null
fi
aws lambda wait function-updated-v2 --function-name $FN --region $R
aws lambda get-function-url-config --function-name $FN --region $R --no-cli-pager >/dev/null 2>&1 || aws lambda create-function-url-config --function-name $FN --auth-type NONE --region $R --no-cli-pager >/dev/null
aws lambda add-permission --function-name $FN --statement-id public-url --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE --region $R --no-cli-pager >/dev/null 2>&1 || true
URL=$(aws lambda get-function-url-config --function-name $FN --region $R --no-cli-pager --query FunctionUrl --output text)
echo "Hosted UI: $URL"
