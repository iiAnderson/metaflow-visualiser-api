from metaflow import Metaflow, Flow, get_metadata, metadata, namespace, Run, Step, Task, DataArtifact
from exception import MetaflowException
from datetime import datetime, timedelta 
from dateutil import parser
import pandas as pd
import numpy as np
import itertools

class MetaflowWrapper(Metaflow):

    def __init__(self):
        super().__init__()

    def get_flows(self):
        for f in self.flows:
            yield FlowWrapper(flow_name="".join(f.path_components))     

    def get_formatted_flows(self):

        formatted_result = []

        for flow in self.get_flows():
            formatted_result.append(flow.get_last_run().json())

        return formatted_result

    def json():
        pass

    def get_count(self, count_categories, key_parser, stop_condition=lambda x:True):

        for flow in self.get_flows():
            count_categories = flow.get_count(count_categories, key_parser, stop_condition)

        return count_categories


class FlowWrapper(Flow):

    def __init__(self, flow_name=None):
        super().__init__(flow_name)

    def json(self):
        return {}

    def get_last_run(self):
        return RunWrapper("/".join(self.latest_run.path_components))

    def get_last_successful_run(self):
        return RunWrapper("/".join(self.latest_successful_run.path_components))

    def get_all_runs(self):
        for r in self.runs():
            print(r.created_at)
            yield RunWrapper("/".join(r.path_components))

    def get_most_recent_runs(self, n):
        return [ RunWrapper("/".join(r.path_components)).json() for r in itertools.islice(list(self.runs()), n)] 

    def get_runs(self, timestamp=(datetime.now() - timedelta(days=1)).timestamp()):

        runs = []

        for r in self.get_all_runs():
            run_date = datetime.strptime(r.created_at.split(".")[0], '%Y-%m-%dT%H:%M:%S').timestamp()

            if run_date > int(timestamp):
                runs.append(r.json())
            else:
                break
        
        return runs

    def get_count(self, count_categories, key_parser, stop_condition):
        
        for run in self.get_all_runs():
            key_formatted = key_parser(run)
            
            if stop_condition(run):
                break

            if key_formatted in count_categories:
                count_categories[key_formatted] = count_categories[key_formatted] + 1
        
        return count_categories


class RunWrapper(Run):

    def __init__(self, run_name=None):
        super().__init__(run_name)

    def is_before(self, unix_timestamp):
        return self.created_at < unix_timestamp

    def get_steps(self):
        for s in self.steps():
            yield StepWrapper(step_name="/".join(s.path_components))

    def get_formatted_steps(self):
        results = []

        for s in self.steps():
            results.append(StepWrapper("/".join(s.path_components)).json())

        return results

    def _parse_tags(self, tags, key_string):
        for tag in tags:
            if key_string in tag:
                return tag.split(":")[-1]
        return None

    def get_run_output_data(self):

        task_wrapper = TaskWrapper(Step(self.pathspec + "/end").task.pathspec)

        return task_wrapper.get_data()

    def json(self):
        return {
            "successful": self.successful,
            "finished": self.finished,
            "finished_at": self.finished_at,
            "created_at": self.created_at,
            'run_id': int(self.path_components[-1]),
            'flow': self.path_components[-2],
            "user": self.user
        }

    def json_with_steps(self):
        return {
            **self.json(), 
            **{"steps": self.get_formatted_steps()}
        }
    
    @property
    def user(self):
        return self._parse_tags(self.tags, "user")
    
    def __str__(self):
        return self.__str__()

class StepWrapper(Step):

    # def __init__(self, flow_name=None, run_id=None, step_name=None):
    #     self._step = Step(f"{flow_name}/{run_id}/{step_name}")

    def __init__(self, step_name=None):
        super().__init__(step_name)

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
        if isinstance(data, pd.DataFrame):
            return data.to_json()

        if isinstance(data, np.ndarray):
            return data.tolist()

        return data

    def json(self):
        json_obj =  {
            "data": self._format(data),
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