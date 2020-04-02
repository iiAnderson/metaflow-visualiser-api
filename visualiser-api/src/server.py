from flask import Flask
from api import route_flows, get_run_data, all_runs_since, count_runs, get_most_recent, get_last_n, get_run_artifacts

app = Flask(__name__)

@app.route("/flows")
def hello():
    return route_flows()

@app.route("/flows/<flow_name>/run/<run_id>")
def run_flows(flow_name, run_id):
    return get_run_data(flow_name, run_id)

@app.route("/flows/<flow_name>/run/<run_id>/artifacts")
def run_artifacts(flow_name, run_id):
    return get_run_artifacts(flow_name, run_id)

@app.route("/flows/<flow_name>/<timestamp>")
def timestamp_specify_flow(flow_name, timestamp):
    return all_runs_since(flow_name=flow_name, timestamp=timestamp)

@app.route("/flows/<timestamp>")
def run_flows_timestamp(timestamp):
    return all_runs_since(flow_name=None, timestamp=timestamp)

@app.route("/flows/count")
def run_flows_count():
    return count_runs()

@app.route("/flows/<flow_name>/count")
def run_flows_count_with_flow(flow_name):
    return count_runs(flow_name)

@app.route("/flows/<flow_name>/recent")
def most_recent_run_for_flow(flow_name):
    return get_most_recent(flow_name)

@app.route("/flows/<flow_name>/last")
def get_last_5_runs(flow_name):
    return get_last_n(flow_name)

@app.after_request # blueprint can also be app~~
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    return response


