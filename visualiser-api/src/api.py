from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run
from exception import MetaflowException
from datetime import datetime, timedelta 
from dateutil import parser
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

def count_flows():
    namespace(None)

    flows = Metaflow().flows

    result = get_week_times()

    for flow in list(flows):
        
        for run in flow.runs():
            print(run.created_at)
            flow_datetime = datetime.strptime(run.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S')
            a_week_ago = (datetime.now() - timedelta(days=7))

            if flow_datetime.timestamp() < a_week_ago.timestamp():
                # Flows are in order, so if we've reached one after a week ago then we can break from execution
                break 

            flow_formatted_time = get_formatted_time(flow_datetime)

            if flow_formatted_time in result:
                result[flow_formatted_time] = result[flow_formatted_time] + 1

    formatted = []

    for key, value in result.items():
        formatted.append({"time": key, "count": value})

    return {"data": formatted}



def get_week_times():
    now = datetime.now()

    days = {}

    for i in [0, 1, 2, 3, 4, 5, 6]:
        n_days_ago = now - timedelta(days=i)
        days[get_formatted_time(n_days_ago)] = 0
    
    return days

def get_formatted_time(datetime_obj):
    return f"{datetime_obj.month}/{datetime_obj.day}"

def route_flows():

    namespace(None)

    flows = Metaflow().flows

    result = []

    for flow in list(flows):
        
        last_run = flow.latest_run

        result.append({
            "project": "test-project",
            "successful": last_run.successful,
            "finished": last_run.finished,
            "finished_at": last_run.finished_at,
            'run_id': int(last_run.path_components[-1]),
            'flow': flow.pathspec
        })

    return {"data": result}

def all_flows_since(timestamp=(datetime.now() - timedelta(days=1)).timestamp()):

    namespace(None)

    flows = Metaflow().flows

    result = []

    for flow in list(flows):
        
        for run in flow.runs():
            print(run.created_at)
            flow_datetime = datetime.strptime(run.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S').timestamp()
            print(flow_datetime)

            if flow_datetime > int(timestamp):
                result.append({
                    "successful": run.successful,
                    "finished": run.finished,
                    "finished_at": run.finished_at,
                    "created_at": run.created_at,
                    'run_id': int(run.path_components[-1]),
                    'flow': flow.pathspec,
                    "user": parse_tags(run.tags, "user")
                }) 

    print(result)
    return {"data": result}

def parse_tags(tags, key_string):
    for tag in tags:
        if key_string in tag:
            return tag.split(":")[-1]
    return None

def get_run_data(flow=None, run_id=None):

    if flow is None or run_id is None:
        raise MetaflowException(400, "Invalid parameters")

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
    "/flows/count": count_flows,
    "/flows/{flow}/{run_id}": get_run_data,
    "/flows/{timestamp}": all_flows_since
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
