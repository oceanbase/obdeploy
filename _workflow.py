# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import os
import sys
from copy import deepcopy

from _manager import Manager
from _plugin import ComponentPluginLoader, pyScriptPluginExec, PyScriptPluginLoader, PyScriptPlugin
from tool import OrderedDict


class WorkflowsIter(object):

    def __init__(self, workflows):
        self.workflows = workflows
        self.stages = []
        for workflow in workflows:
            self.stages += workflow.stages
        self.stages = sorted(set(self.stages))
        self.index = 0
        self.lentgh = len(self.stages)

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < self.lentgh:
            stage = self.stages[self.index]
            self.index += 1
            stages = OrderedDict()
            for workflow in self.workflows:
                stages[workflow.component_name] = workflow[stage]
            return stages
        else:
            raise StopIteration


class Workflows(object):

    def __init__(self, name):
        self.name = name
        self.workflows = {}

    def __getitem__(self, component_name):
        if component_name not in self.workflows:
            self.workflows[component_name] = ComponentWorkflow(self.name, component_name)
        return self.workflows[component_name]
    
    def __len__(self):
        return len(self.workflows)
    
    def __setitem__(self, component_name, component_workflow):
        if not isinstance(component_workflow, ComponentWorkflow):
            raise TypeError("%s must be a instance of ComponentWorkflow" % component_workflow.__class__.__name__)
        if component_workflow.name != self.name:
            raise ValueError("%s is not a %s workflow" % (component_workflow, self.name))
        self.workflows[component_name] = component_workflow
    
    def __call__(self, sorted_components):
        workflows = [
            self[component] for component in sorted_components
        ]
        return WorkflowsIter(workflows)
    

class SubWorkflows(object):

    def __init__(self) -> None:
        self.workflows = OrderedDict()

    def add(self, workflow):
        if not isinstance(workflow, ComponentWorkflow):
            raise TypeError("%s must be a instance of ComponentWorkflow" % workflow.__class__.__name__)
        if workflow.name not in self.workflows:
            self.workflows[workflow.name] = Workflows(workflow.name)
        self.workflows[workflow.name][workflow.component_name] = workflow

    def __getitem__(self, workflow_name):
        return self.workflows[workflow_name]
    
    def __iter__(self):
        return iter(self.workflows.values())


class SubWorkflowTemplate(object):
    
    def __init__(self, name, component_name, version=None, kwargs=None):
        self.name = name
        self.component_name = component_name
        self.version = version
        self.kwargs = kwargs or {}


class PluginTemplate(object):

    def __init__(self, name, component_name, version=None, kwargs=None):
        self.name = name
        self.component_name = component_name
        self.version = version
        self.kwargs = kwargs or {}


class ComponentWorkflow(object):

    def __init__(self, name, component_name):
        self.name = name
        self.component_name = component_name
        self.stage = {}
        self.sub_workflow = {}
        self.global_kwargs = {}

    def set_global_kwargs(self, **kwargs):
        self.global_kwargs = kwargs

    def add(self, stage, *plugins):
        return self.add_with_kwargs(stage, None, *plugins)

    def add_with_component(self, stage, component_name, *plugins):
        return self.add_with_component_version(stage, component_name, None, *plugins)

    def add_with_component_version(self, stage, component_name, version, *plugins):
        return self.add_with_component_version_kwargs(stage, component_name, version, None, *plugins)

    def add_with_kwargs(self, stage, kwargs, *plugins):
        return self.add_with_component_version_kwargs(stage, self.component_name, None, kwargs, *plugins)

    def add_with_component_version_kwargs(self, stage, component_name, version, kwargs, *plugins):
        stage = int(stage)
        plugins = [PluginTemplate(plugin, component_name, version, kwargs) for plugin in plugins]
        if stage not in self.stage:
            self.stage[stage] = plugins
        else:
            if stage in self.sub_workflow:
                raise Exception("stage %s already has a workflow" % stage)
            self.stage[stage] += plugins

    def add_workflow(self, stage, workflow):
        return self.add_workflow_with_kwargs(stage, None, workflow)
    
    def add_workflow_with_component(self, stage, component_name, workflow):
        return self.add_workflow_with_component_version(stage, component_name, None, workflow)
    
    def add_workflow_with_component_version(self, stage, component_name, version, workflow):
        return self.add_workflow_with_component_version_kwargs(stage, component_name, version, None, workflow)
    
    def add_workflow_with_kwargs(self, stage, kwargs, workflow):
        return self.add_workflow_with_component_version_kwargs(stage, self.component_name, None, kwargs, workflow)
    
    def add_workflow_with_component_version_kwargs(self, stage, component_name, version, kwargs, workflow):
        stage = int(stage)
        workflow = SubWorkflowTemplate(workflow, component_name, version, kwargs)
        if stage not in self.stage:
            self.stage[stage] = [workflow]
            self.sub_workflow[stage] = workflow
        else:
            raise Exception("stage %s already has a workflow" % stage)
                            
    @property
    def stages(self):
        return sorted(self.stage.keys())
    
    def __getitem__(self, stage):
        if self.global_kwargs:
            stages = []
            for template in self.stage.get(stage, []):
                template = deepcopy(template)
                template.kwargs.update(self.global_kwargs)
                stages.append(template)
            return stages
        else:
            return self.stage.get(stage, [])


class ComponentWorkflowLoader(ComponentPluginLoader):
    MODULE_NAME = __name__


def workflowTemplateExec(func):
    def _new_func(
        self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs
        ):
        workflow = ComponentWorkflow(self.name, self.component_name)
        ret = pyScriptPluginExec(func)(self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, [], cluster_config, cmd,
        options, stdio, workflow, *arg, **kwargs)
        return workflow if ret else None
    return _new_func


class WorkflowLoader(ComponentWorkflowLoader):

    def __init__(self, home_path, workflow_name=None, dev_mode=False, stdio=None):
        if not workflow_name:
            raise NotImplementedError
        type_name = 'PY_SCRIPT_WORKFLOW_%s' % workflow_name.upper()
        type_value = 'PyScriptWorkflow%sPlugin' % ''.join([word.capitalize() for word in workflow_name.split('_')])
        self.PLUGIN_TYPE = PyScriptPluginLoader.PyScriptPluginType(type_name, type_value)
        if not getattr(sys.modules[__name__], type_value, False):
            self._create_(workflow_name)
        super(WorkflowLoader, self).__init__(home_path, dev_mode=dev_mode, stdio=stdio)
        self.workflow_name = workflow_name

    def _create_(self, workflow_name):
        exec('''
class %s(PyScriptPlugin):

    FLAG_FILE = '%s.py'
    PLUGIN_NAME = '%s'

    def __init__(self, component_name, plugin_path, version, dev_mode):
        super(%s, self).__init__(component_name, plugin_path, version, dev_mode)

    @staticmethod
    def set_plugin_type(plugin_type):
        %s.PLUGIN_TYPE = plugin_type

    @workflowTemplateExec
    def %s(
        self, namespace, namespaces, deploy_name, deploy_status,
        repositories, components, clients, cluster_config, cmd,
        options, stdio, *arg, **kwargs):
        pass
        ''' % (self.PLUGIN_TYPE.value, workflow_name, workflow_name, self.PLUGIN_TYPE.value, self.PLUGIN_TYPE.value, workflow_name))
        clz = locals()[self.PLUGIN_TYPE.value]
        setattr(sys.modules[__name__], self.PLUGIN_TYPE.value, clz)
        clz.set_plugin_type(self.PLUGIN_TYPE)
        return clz


class ComponentWorkflowLoader(WorkflowLoader):

    def __init__(self, home_path, component_name, workflow_name=None, dev_mode=False, stdio=None):
        super(ComponentWorkflowLoader, self).__init__(os.path.join(home_path, component_name), workflow_name, dev_mode=dev_mode, stdio=stdio)
        self._general_loader = WorkflowLoader(os.path.join(home_path, "general"), workflow_name, dev_mode=dev_mode, stdio=stdio)
        self._general_loader.component_name = component_name


    def get_workflow_template(self, version):
        template = self.get_best_plugin(version)
        if not template:
            if not version:
                version = '0.1'
            template = self._general_loader.get_best_plugin(version)
        return template


class WorkflowManager(Manager):

    RELATIVE_PATH = 'workflows'
    # The directory structure for plugin is ./workflows/{component_name}/{version}

    def __init__(self, home_path, dev_mode=False, stdio=None):
        super(WorkflowManager, self).__init__(home_path, stdio=stdio)
        self.workflow_loaders = {}
        self.dev_mode = dev_mode

    def get_loader(self, workflow_name, component_name):
        if component_name not in self.workflow_loaders:
            self.workflow_loaders[component_name] = {}
        if workflow_name not in self.workflow_loaders[component_name]:
            self.workflow_loaders[component_name][workflow_name] = ComponentWorkflowLoader(self.path, component_name, workflow_name, self.dev_mode, stdio=self.stdio)
        return self.workflow_loaders[component_name][workflow_name]

    def get_workflow_template(self, workflow_name, component_name, version):
        loader = self.get_loader(workflow_name, component_name)
        return loader.get_workflow_template(version)
