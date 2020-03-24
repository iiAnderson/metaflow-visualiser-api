from flask import Flask
from api import route_flows, get_run_data, all_flows_since, count_flows

app = Flask(__name__)

@app.route("/flows")
def hello():
    return route_flows()

@app.route("/flows/<flow>/<run_id>")
def run_flows(flow, run_id):
    return get_run_data(flow, run_id)

@app.route("/flows/<timestamp>")
def run_flows_timestamp(timestamp):
    return all_flows_since(timestamp)

@app.after_request # blueprint can also be app~~
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    return response

@app.route("/flows/count")
def run_flows_count():
    return count_flows()