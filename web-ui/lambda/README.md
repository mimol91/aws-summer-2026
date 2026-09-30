# GovEase web UI (Lambda)

Single-page chat UI served by the `AgentCore-govease-web` Lambda (function URL).

- `handler.py`: GET `/` page, POST `/uaepass` (simulated UAE PASS sign-in, creates a Cognito user per phone number), POST `/upload-url` (presigned S3 PUT for a citizen's new PDF into `citizens/<id>/`), POST `/chat` (calls the AgentCore runtime with the user's Cognito token).
- `index.html`: the page (EN/AR, RTL).
- `local_server.py`: runs the handler locally on :8502.

Env vars: `RUNTIME_ARN`, `COGNITO_CLIENT_ID`, `USER_POOL_ID` (unset disables `/uaepass`).
The role needs `cognito-idp:AdminCreateUser` and `AdminSetUserPassword` on the pool.

Deploy:

    zip -q -r new.zip handler.py index.html
    aws lambda update-function-code --function-name AgentCore-govease-web --zip-file fileb://new.zip --region us-west-2

Local (needs boto3): `AWS_REGION=us-west-2 USER_POOL_ID=... RUNTIME_ARN=... COGNITO_CLIENT_ID=... python local_server.py`

Uploads: the role needs `s3:PutObject` on `<documents-bucket>/citizens/*` and `ssm:GetParameter` on `/app/workshop/govease/documents-bucket`;
the bucket needs a CORS rule allowing `PUT` (header `Content-Type`) from the function URL origin.
The citizen id is entered in the page (demo-grade trust): a real deployment must map the verified identity to a citizen record.
