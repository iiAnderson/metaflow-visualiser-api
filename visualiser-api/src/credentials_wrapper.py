import requests
import os
import json
import time
from exception import MetaflowException

CREDENTIALS_API_URL = os.environ['CREDENTIALS_API_URL']
from aws_xray_sdk.core import patch_all
from aws_xray_sdk.core import xray_recorder

patch_all()
def lambda_handler(event, context):

    x_api_key = event['headers']['x-api-key']

    response = requests.get(
        CREDENTIALS_API_URL,
        headers={'x-api-key': x_api_key}
    )

    if response.status_code == requests.codes.ok:
        metaflow_creds = response.json()
        print(metaflow_creds)

        for key in metaflow_creds.keys():
            os.environ[key] = metaflow_creds[key]

        os.environ['USERNAME'] = 'metaflow-visualiser'
        subsegment = xray_recorder.begin_subsegment('load_metaflow')
        import api
        xray_recorder.end_subsegment()

        return api.handle_request(event, context)

    else:
        print("Unable to locate credentials")
        return {
            'statusCode': 403,
            'body': json.dumps("Could not obtain Metaflow credentials")
        }

