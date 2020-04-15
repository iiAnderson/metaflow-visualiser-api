import requests
import os
import json
import time
from exception import MetaflowException

CREDENTIALS_API_URL = os.environ['CREDENTIALS_API_URL']
API_KEY = os.environ['API_KEY']

def lambda_handler(event, context):

    response = requests.get(
        CREDENTIALS_API_URL,
        headers={'x-api-key': API_KEY}
    )

    if response.status_code == requests.codes.ok:
        metaflow_creds = response.json()
        print(metaflow_creds)

        with open("/tmp/config.json", 'w+') as f:
            json.dump(metaflow_creds, f)
            print("written file")

        import api

        return api.handle_request(event, context)

    else:
        print("Unable to locate credentials")
        return {
            'statusCode': 403,
            'body': json.dumps("Could not obtain Metaflow credentials")
        }

