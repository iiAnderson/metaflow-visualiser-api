#!/bin/sh
set -e

usage() {
    echo "./deploy"
}

POSITIONAL=()
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        --metaflow-bucket|--mb)
        metaflow_bucket="$2"
        shift 2 # Shift pass arg and val
        ;;
        --artifact-bucket|--ab)
        artifact_bucket="$2"
        shift 2 
        ;;
        --events-store|--es)
        events_store="$2"
        shift 2 
        ;;
        --events-store-index|--esi)
        events_store_index="$2"
        shift 2 
        ;;
        --credentials-url|--cu)
        credentials_url="$2"
        shift 2 
        ;;
        --api-key|--ak)
        api_key_ref="$2"
        shift 2 
        ;;
        --profile|--p)
        profile="$2"
        shift 2  
        ;;
        *)    # unknown option
        POSITIONAL+=("$1") # save it in an array for later
        shift # past argument
        ;;
    esac
done
set -- "${POSITIONAL[@]}"

if [ -z "$profile" ]; then
    profile="default"
fi

custom_resource="custom-resource.zip"
events_processor="events-processor.zip"
visualiser_api="visualiser-api.zip"

./upload_lambda.sh "$custom_resource" "custom-resource" $bucket $profile
./upload_lambda.sh "$events_processor" "events-processor" $bucket $profile
./upload_lambda.sh "$visualiser_api" "visualiser-api" $bucket $profile

# Params

aws cloudformation deploy --template-file capture.yml --stack-name metaflow-events \
        --parameter-overrides \
            MetaflowBucket="$metaflow_bucket" \
            MetaflowEventProcessorPath="s3://$bucket/$events_processor" \
            CustomResourceLambdaPath="s3://$bucket/$custom_resource"  \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --profile "$profile"