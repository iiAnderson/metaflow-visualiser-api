from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run
from wrappers import RunWrapper, FlowWrapper, StepWrapper, MetaflowWrapper
from exception import MetaflowException
from datetime import datetime, timedelta 
from dateutil import parser
from statistics import mean
from boto3.dynamodb.conditions import Key, Attr
import re
import boto3
import json
import itertools

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

'''

    Endpoints returning Run data

'''

def route_flows():

    namespace(None)

    m_wrapper = MetaflowWrapper()
    result = m_wrapper.get_formatted_flows()

    return {"data": result}

def all_runs_since(flow_name=None,timestamp=(datetime.now() - timedelta(days=1)).timestamp()):

    runs = FlowWrapper(flow_name=flow_name).get_runs(timestamp=timestamp)

    return { "data": sorted(runs, key = lambda r: (r['created_at']), reverse=True) }


def get_most_recent(flow_name):
    namespace(None)

    flow = FlowWrapper(flow_name)

    last_run = flow.get_last_successful_run().json_with_steps()

    if last_run is None:
        return {}
    
    return {"data": last_run}

def get_last_n(flow_name, n=5):
    namespace(None)

    flow = FlowWrapper(flow_name)
    
    runs = flow.get_most_recent_runs(n)
        
    return {"data": runs}

'''

    Endpoints returning statistics information

'''

def count_runs(flow_name=None):
    namespace(None)

    count_categories = get_week_times()

    def key_parser(run):
        return get_formatted_time(datetime.fromtimestamp(run.created_at))

    def stop_condition(run):
        a_week_ago = (datetime.now() - timedelta(days=7))
        flow_datetime = datetime.fromtimestamp(run.created_at)

        return flow_datetime.timestamp() < a_week_ago.timestamp()

    if flow_name is None:
        return_counts = MetaflowWrapper().get_count(count_categories, key_parser, stop_condition)
    else:
        return_counts = FlowWrapper(flow_name=flow_name).get_count(count_categories, key_parser, stop_condition)

    return_data = []

    for key, value in return_counts.items():
        return_data.append({"time": key, "count": value})

    return { "data": return_data } 

def get_week_times():
    now = datetime.now()

    days = {}

    for i in [0, 1, 2, 3, 4, 5, 6]:
        n_days_ago = now - timedelta(days=i)
        days[get_formatted_time(n_days_ago)] = 0
    
    return days

def get_formatted_time(datetime_obj):
    return f"{datetime_obj.month}/{datetime_obj.day}"

def get_datetime_from_string(time):
    return datetime.strptime(time.split(".")[0], '%Y-%m-%dT%H:%M:%S')

def run_generic_statistics(flow_name):

    flow = FlowWrapper(flow_name)

    last_run_id = flow.latest_run.path_components[-1]

    return {
        "data": {
            **{"last_run_id": last_run_id, 
            **calculate_basic_statistics(flow.get_all_runs())}
        }
    }

def calculate_basic_statistics(runs):

    times = []
    users = []

    for run in runs:
        # Calcuate avg completion time
        created = get_datetime_from_string(run.created_at)

        if run.finished_at is None:
            continue

        finished = get_datetime_from_string(run.finished_at)

        delta = finished - created
        times.append(delta.total_seconds())

        # Calculate most popular user
        users.append(run.user)

    avg_time = mean(times)
    common_user = max(set(users), key=users.count)

    return {
        "average_execution_time": avg_time,
        "most_common_user": common_user
    }


'''

    Endpoints which return step data

'''

def get_run_data(flow=None, run_id=None):

    if flow is None or run_id is None:
        raise MetaflowException(400, "Invalid parameters")

    namespace(None)
    run = RunWrapper(f"{flow}/{run_id}")

    return {
        "data": run.get_formatted_steps()
    }


'''

    Endpoints which return DataArtifacts

'''

def get_run_artifacts(flow=None, run_id=None):
    if flow is None or run_id is None:
        raise MetaflowException(400, "Invalid parameters")

    namespace(None)
    run = RunWrapper.create_from_lookup(flow, run_id)

    return {
        "data": run.get_run_output_data()
    }


registered_endpoints = {
    "/flows/": route_flows, # Gets all flows
    "/flows/count": count_runs, # Count all flows
    "/flows/{timestamp}": all_runs_since, # Returns all runs within timestamp
    "/flows/{flow_name}/count": count_runs, # Returns count of runs for flow
    "/flows/{flow_name}/run/{run_id}": get_run_data, # Returns specific run
    "/flows/{flow_name}/{timestamp}": all_runs_since, # Returns runs filtered by time
    "/flows/{flow_name}/recent": get_most_recent, # Returns runs filtered by time
    "/flows/{flow_name}/last": get_most_recent # Returns runs filtered by time

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

