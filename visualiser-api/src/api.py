from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run
from wrappers import RunWrapper, FlowWrapper, StepWrapper, MetaflowWrapper
from exception import MetaflowException
from datetime import datetime, timedelta 
from dateutil import parser
import re
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
    
    namespace(None)

    if flow_name is None:
        flows = MetaflowWrapper().get_flows()
    else:
        flows = [FlowWrapper(flow_name=flow_name)]

    return_runs = []

    for flow in flows:
        return_runs.extend(flow.get_runs(timestamp=timestamp))

    return {"data": sorted(return_runs, key = lambda r: (r['created_at']))}

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

    Endpoints returning count information

'''

def count_runs(flow_name=None):
    namespace(None)

    count_categories = get_week_times()

    def key_parser(run):
        return get_formatted_time(datetime.strptime(run.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S'))

    def stop_condition(run):
        a_week_ago = (datetime.now() - timedelta(days=7))
        flow_datetime = datetime.strptime(run.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S')

        return flow_datetime.timestamp() < a_week_ago.timestamp()

    if flow_name is None:
        return_counts = MetaflowWrapper().get_count(count_categories, key_parser, stop_condition)
    else:
        return_counts = FlowWrapper(flow_name=flow_name).get_count(count_categories, key_parser, stop_condition)

    return_data = []

    for key, value in return_counts.items():
        return_data.append({"time": key, "count": value})

    return {"data": return_data} 

def get_week_times():
    now = datetime.now()

    days = {}

    for i in [0, 1, 2, 3, 4, 5, 6]:
        n_days_ago = now - timedelta(days=i)
        days[get_formatted_time(n_days_ago)] = 0
    
    return days

def get_formatted_time(datetime_obj):
    return f"{datetime_obj.month}/{datetime_obj.day}"

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


