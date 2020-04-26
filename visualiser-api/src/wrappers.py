from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run, Step, Task, DataArtifact
from exception import MetaflowException
from datetime import datetime, timedelta
from dateutil import parser
import boto3
from boto3.dynamodb.conditions import Key, Attr
# import pandas as pd
import time
import json
import boto3
import os
# import numpy as np
import itertools

# (flow_name, created_at)
EVENTS_SOURCE_STORE = os.environ['EVENTS_SOURCE_STORE']
# run_id index (flow_name, run_id)
EVENTS_SOURCE_INDEX = os.environ['EVENTS_SOURCE_INDEX']


def metadata(func):
    def wrapper(*args):
        run = args[0]

        if run.cache:
            namespace(None)
            run._run = Run(run.pathspec)
            run.cache = False

        return func(run)

    return wrapper


class MetaflowWrapper():

    def __init__(self):
        super().__init__()
        namespace(None)
        self._metaflow = Metaflow()

    def get_flows(self):

        return [FlowWrapper(flow_name=f.path_components[-1]) for f in self._metaflow.flows]

    def get_formatted_flows(self):

        formatted_result = []

        for flow in self.get_flows():
            formatted_result.append(flow.get_last_run().json())

        return formatted_result

    def json():
        pass

    def get_count(self, count_categories, key_parser, stop_condition=lambda x: True):

        for flow in self.get_flows():
            count_categories = flow.get_count(
                count_categories, key_parser, stop_condition)

        return count_categories


class FlowWrapper():

    def __init__(self, flow_name=None):
        self._flow_name = flow_name
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        self._table = dynamodb.Table('metaflow-events-store')

    def get_all_runs(self, timestamp=None):

        if timestamp:
            kce = Key('flow_name').eq(self._flow_name) & Key(
                'created_at').between(int(timestamp), int(datetime.now().timestamp()))

            response = self._table.query(
                KeyConditionExpression=kce, ScanIndexForward=False)
        else:
            fe = Key('flow_name').eq(self._flow_name)
            response = self._table.scan(
                FilterExpression=fe
            )

        if 'Items' in response:
            for item in response['Items']:
                yield RunWrapper.create_from_cache(item)

    def get_last_run(self):

        kce = Key('flow_name').eq(self._flow_name) & Key(
            'run_id').between(0, 10000)
        output = self._table.query(
            KeyConditionExpression=kce, ScanIndexForward=False, Limit=1, IndexName=EVENTS_SOURCE_INDEX)

        if 'Items' in output:
            return RunWrapper.create_from_cache(output['Items'][0])

        return {}

    def get_last_successful_run(self):

        kce = Key('flow_name').eq(self._flow_name) & Key(
            'run_id').between(0, 1000000)
        fe = Key('success').eq(True)
        output = self._table.query(KeyConditionExpression=kce, FilterExpression=fe,
                                   ScanIndexForward=False, IndexName=EVENTS_SOURCE_INDEX)
        print(output)
        if 'Items' in output:
            return RunWrapper.create_from_cache(output['Items'][0])

        return {}

    def get_most_recent_runs(self, n):

        kce = Key('flow_name').eq(self._flow_name) & Key(
            'run_id').between(0, 10000)
        output = self._table.query(
            KeyConditionExpression=kce, ScanIndexForward=False, Limit=n, IndexName=EVENTS_SOURCE_INDEX)

        runs = []

        if 'Items' in output:
            for run in output['Items']:
                runs.append(RunWrapper.create_from_cache(run).json())

        return runs

    def get_runs(self, timestamp=(datetime.now() - timedelta(days=1)).timestamp()):

        runs = []

        for r in self.get_all_runs(timestamp=timestamp):
            runs.append(r.json())

        print(runs)
        return runs

    def get_count(self, count_categories, key_parser, stop_condition):

        for run in self.get_all_runs():
            key_formatted = key_parser(run)

            if stop_condition(run):
                break

            if key_formatted in count_categories:
                count_categories[key_formatted] = count_categories[key_formatted] + 1

        return count_categories

    def json(self):
        return {
            "flow_name": self._flow_name
        }


class RunWrapper():

    @staticmethod
    def create_from_lookup(flow_name, run_id):
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        _table = dynamodb.Table('metaflow-events-store')

        kce = Key('flow_name').eq(flow_name) & Key('run_id').eq(int(run_id))
        output = _table.query(KeyConditionExpression=kce,
                              ScanIndexForward=False, Limit=1, IndexName=EVENTS_SOURCE_INDEX)

        if 'Items' in output:
            return RunWrapper.create_from_cache(output['Items'][0])

        raise Exception("Not found")

    @staticmethod
    def create_from_cache(item):

        run = RunWrapper()
        run.cache = True

        run.created_at = int(item['created_at'])
        run.finished_at = int(item['finished_at'])
        run.successful = item['success']
        run.finished = item['finished']
        run.user = item['user']
        run.current_step = item['current_step']
        run.tags = item['tags']
        run.run_id = int(item['run_id'])
        run.flow_name = item['flow_name']

        return run

    @staticmethod
    def create_from_metadata(metadata):

        run = RunWrapper()
        run.cache = False
        run._run = metadata

        return run

    def is_before(self, unix_timestamp):
        return self.created_at < unix_timestamp

    @metadata
    def get_steps(self):

        for s in self._run.steps():
            yield StepWrapper(step_name=s.pathspec)

    @metadata
    def get_formatted_steps(self):
        results = []
        st = time.time()
        for s in self._run.steps():
            results.append(StepWrapper(s.pathspec).json_without_tasks())
        e = time.time()
        return results

    @metadata
    def _parse_tags(self, tags, key_string):
        for tag in tags:
            if key_string in tag:
                return tag.split(":")[-1]
        return None

    @metadata
    def get_run_output_data(self):

        task_wrapper = TaskWrapper(self._run.end_task.pathspec)

        return task_wrapper.get_data()

    def json(self):
        return {
            "success": self.successful,
            "finished": self.finished,
            "finished_at": int(self.finished_at),
            "created_at": int(self.created_at),
            'run_id': int(self.get_run_id()),
            'flow': self.get_flow_name(),
            "user": self.user
        }

    @property
    def pathspec(self):
        return f"{self.get_flow_name()}/{self.get_run_id()}" if self.cache else self._run.pathspec

    def get_run_id(self):
        return self.run_id if self.cache else int(self.path_components[-1])

    def get_flow_name(self):
        return self.flow_name if self.cache else int(self.path_components[-2])

    def json_with_steps(self):
        return {
            **self.json(),
            **{"steps": self.get_formatted_steps()}
        }


class StepWrapper(Step):

    def __init__(self, step_name=None):
        super().__init__(step_name)

    def json_without_tasks(self):
        return {
            "step": self.path_components[-1],
            "finished_at": self.finished_at,
            "created_at": self.created_at
            # "tasks": self.get_formatted_tasks()
        }

    def json(self):
        return {
            "step": self.path_components[-1],
            "finished_at": self.finished_at,
            "created_at": self.created_at,
            "tasks": self.get_formatted_tasks()
        }

    def get_tasks(self):
        for task in self.tasks():
            yield TaskWrapper("/".join(s.path_components))

    def get_formatted_tasks(self):

        results = []
        for s in self.tasks():
            results.append(TaskWrapper("/".join(s.path_components)).json())

        return results


class TaskWrapper(Task):

    def __init__(self, task_name=None):
        super().__init__(task_name)

    def get_data(self):
        return_dataset = {}

        for data in self.artifacts:

            wrapper = DataArtifactWrapper(data.pathspec).json()
            return_dataset[wrapper['artifact_name']] = wrapper

        return return_dataset

    def json(self):
        return {
            "successful": self.successful,
            "finished": self.finished,
            "finished_at": self.finished_at,
            "created_at": self.created_at,
            "exception": self.exception,
            "stdout": self.stdout,
            "stderr": self.stderr
        }


class DataArtifactWrapper(DataArtifact):

    def __init__(self, artifact_name=None):
        super().__init__(artifact_name)

    def _format(self, data):
        # if isinstance(data, pd.DataFrame):
        #     return data.to_json()

        # if isinstance(data, np.ndarray):
        #     return data.tolist()

        return data

    def json(self):
        json_obj = {
            "data": self._format(self.data),
            "artifact_name": self.path_components[-1],
            "finished_at": self.finished_at
        }

        try:
            json.dumps(json_obj)

            # Successfully serialised, so we know it's serialisable
            return json_obj
        except (TypeError, OverflowError):
            return {
                "data": f"There was an error when converting {self.path_components[-1]} to JSON"
            }
