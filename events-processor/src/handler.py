import json
import os
import boto3
from datetime import datetime

EVENTS_RECORD_STORE = os.environ['EVENTS_RECORD_STORE']
dynamodb = boto3.resource('dynamodb')

def _parse_tags(tags, key_string):
    for tag in tags:
        if key_string in tag:
            return tag.split(":")[-1]
    return None

def lambda_handler(event, context):

    print(event)

    for record in event['Records']:
        key = record['s3']['object']['key']
        bucket_name = record['s3']['bucket']['name']

        os.environ['METAFLOW_HOME'] = '/tmp'
        os.environ['USERNAME'] = "events-processor"

        obj = {
            'METAFLOW_DEFAULT_METADATA': 'service',
            'METAFLOW_DEFAULT_DATASTORE': 's3',
            'METAFLOW_DATASTORE_SYSROOT_S3': f"s3://{bucket_name}" ,
            'METAFLOW_SERVICE_AUTH_KEY': "yvhNDfEzcRa5fxKq2ZELda1zk8wNXxMs17Jt4OGs",
            'METAFLOW_SERVICE_URL': "https://5sqcgnuyte.execute-api.eu-west-1.amazonaws.com/api/"
        }

        with open('/tmp/config.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=4)

        from metaflow import Run, get_metadata, namespace

        namespace(None)
        print(get_metadata())

        step = key.split("/")[2]
        flow = key.split("/")[0]
        run_id = key.split("/")[1]

        run = Run(f"{flow}/{run_id}")

        dynamo_object = {
            "created_at": int(datetime.strptime(run.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S').timestamp()),
            "flow_name": flow,
            "run_id":  int(run_id),
            "success": run.successful,
            "finished": run.finished,
            "finished_at": 0 if run.finished_at == None else int(datetime.strptime(run.finished_at.split(".")[0], '%Y-%m-%dT%H:%M:%S').timestamp()),
            "current_step": step,
            "user": _parse_tags(run.tags, "user"),
            "tags": run.tags
        }

        print(dynamo_object)

        table = dynamodb.Table(EVENTS_RECORD_STORE)

        table.put_item(Item=dynamo_object)

    return
