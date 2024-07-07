#!/bin/bash
set -e

if [[ -d "infra" ]]; then
    cd infra

    echo "Install AWS CDK version ${CDK_VERSION}.."

    npm i -g aws-cdk@${CDK_VERSION}
    npm ci --include=dev

    echo "Synthesize infra.."
    echo "1 '${APPLICATION_NAME}'"
    echo "2 '${AWS_ACCOUNT_ID}'"
    echo "3 '${AWS_REGION}'"
    echo "4 '${API_KEY}'"
    echo "5 '${APPLICATION_TAG}'"
    npm run cdk synth -- \
        --context name=${APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context apiKey=${API_KEY} \
        --context applicationTag=${APPLICATION_TAG}
fi