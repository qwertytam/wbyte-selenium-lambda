#!/bin/bash
set -e

if [[ -d "infra" ]]; then
    cd infra

    echo "Install AWS CDK version ${CDK_VERSION}.."

    npm i -g aws-cdk@${CDK_VERSION}
    npm ci --include=dev

    echo "Synthesize infra.."
    echo ${APPLICATION_NAME}
    echo ${AWS_ACCOUNT_ID}
    echo ${AWS_REGION}
    echo ${API_KEY}
    echo ${APPLICATION_TAG}
    npm run cdk synth -- \
        --context name=${APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context apiKey=${API_KEY} \
        --context applicationTag=${APPLICATION_TAG}
fi