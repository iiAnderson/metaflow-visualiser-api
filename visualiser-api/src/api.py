from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run
from exception import MetaflowException
import re
import json

def get_request_info(event):

    route = event['routeKey'].split(" ")[-1]
    values = event['rawPath'].split(" ")[-1].split('/')

    parameters = {}

    for i, r in enumerate(route.split("/")):
        if "{" in r and "}" in r:
            variable = re.search(r'{(.*?)}',r).group(1)
            parameters[variable] = values[i]
    
    return {
        "route": route,
        "operation": event['routeKey'].split(" ")[0],
        "parameters": parameters
    }

def route_flows():

    namespace(None)

    flows = Metaflow().flows

    result = {}

    for flow in list(flows):
        
        last_run = flow.latest_run

        result[flow.pathspec] = {
            "successful": last_run.successful,
            "finished": last_run.finished,
            "finished_at": last_run.finished_at,
            'run_id': int(last_run.path_components[-1]),
            'flow': flow.pathspec
        }   

    return result

def get_run_data(flow=None, run_id=None):

    if flow is None or run_id is None:
        MetaflowException(400, "Invalid parameters")

    namespace(None)

    run = Run(f"{flow}/{run_id}")
    result = {
        'flow': flow,
        'run_id': run_id,
        'steps': []
    }

    for step in reversed(list(run.steps())):
        
        tasks = []

        for task in step.tasks():

            tasks.append({
                "successful": task.successful,
                "finished": task.finished,
                "finished_at": task.finished_at,
                "exception": task.exception,
                "stdout": task.stdout
            })


        result['steps'].append({
            "step": step.path_components[-1],
            "finished_at": step.finished_at,
            "tasks": tasks
        })

            
    return result

registered_endpoints = {
    "/flows": route_flows,
    "/flows/{flow}/{run_id}": get_run_data
}

def lambda_handler(event, context):

    info = get_request_info(event)

    try:
        data = registered_endpoints[info['route']](**info['parameters'])
        print(data)
    except MetaflowException as m:
        return {
            'statusCode': m.http_code,
            'body': json.dumps(message)
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps("Server Error")
        }

    return {
        'statusCode': 200,
        'body': json.dumps(data)
    }
