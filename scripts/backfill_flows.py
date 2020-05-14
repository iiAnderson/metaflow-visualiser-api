from metaflow import Flow, Metaflow, namespace
import boto3

# EVENTS_RECORD_STORE = os.environ['EVENTS_RECORD_STORE']
dynamodb = boto3.resource('dynamodb')

def parse_tags(self, tags, key_string):
    for tag in tags:
        if key_string in tag:
            return tag.split(":")[-1]
    return None

data = []
namespace(None)
for flow in Metaflow().flows:

    for run in flow.runs():

        for step in run.steps():
            print(step)


        run_id = run.path_components[1]
        flow_name = run.path_components[0]

        # time to complete
        # steps
        # artifact location?

        data.append({
            "success": run.successful,
            "finished": run.finished,
            "finished_at": 0 if run.finished_at == None else int(datetime.strptime(run.finished_at, '%Y-%m-%dT%H:%M:%S.fZ')),
            "created_at": int(datetime.strptime(run.created_at, '%Y-%m-%dT%H:%M:%S.fZ')),
            'run_id': int(run_id),
            'flow': flow_name,
            "user": parse_tags(run.tags, "user"),
            "current_step": step,
            "tags": run.tags,
            "bucket": bucket_name
        })

        # print(dynamo_object)

        # table = dynamodb.Table(EVENTS_RECORD_STORE)

        # table.put_item(Item=dynamo_object)

print(data)


