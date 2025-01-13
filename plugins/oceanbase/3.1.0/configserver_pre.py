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

import json
import requests
from urllib.parse import urlparse

from _errno import EC_OBSERVER_FAILED_TO_REGISTER, EC_OBSERVER_FAILED_TO_REGISTER_WITH_DETAILS

from tool import NetUtil


def get_ob_configserver_cfg_url(obconfig_url, appname, stdio):
    parsed_url = urlparse(obconfig_url)
    host = parsed_url.netloc
    stdio.verbose('obconfig_url host: %s' % host)
    url = '%s://%s/debug/pprof/cmdline' % (parsed_url.scheme, host)
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code != 200:
            stdio.verbose('request %s status_code: %s' % (url, str(response.status_code)))
            return None
    except Exception:
        stdio.verbose('Configserver url check failed: request %s failed' % url)
        return None

    if obconfig_url[-1] == '?':
        link_char = ''
    elif obconfig_url.find('?') == -1:
        link_char = '?'
    else:
        link_char = '&'
    cfg_url = '%s%sAction=ObRootServiceInfo&ObCluster=%s' % (obconfig_url, link_char, appname)
    return cfg_url


def config_url(ocp_config_server, appname, cid):
    if ocp_config_server[-1] == '?':
        link_char = ''
    elif ocp_config_server.find('?') == -1:
        link_char = '?'
    else:
        link_char = '&'
    cfg_url = '%s%sAction=ObRootServiceInfo&ObCluster=%s' % (ocp_config_server, link_char, appname)
    # Command that clears the URL content for the cluster
    cleanup_config_url_content = '%s%sAction=DeleteObRootServiceInfoByClusterName&ClusterName=%s' % (ocp_config_server, link_char, appname)
    # Command that register the cluster information to the Config URL
    register_to_config_url = '%s%sAction=ObRootServiceRegister&ObCluster=%s&ObClusterId=%s' % (ocp_config_server, link_char, appname, cid)
    return cfg_url, cleanup_config_url_content, register_to_config_url


def init_config_server(ocp_config_server, appname, cid, force_delete, stdio):
    def post(url):
        stdio.verbose('post %s' % url)
        response = requests.post(url)
        if response.status_code != 200:
            raise Exception('%s status code %s' % (url, response.status_code))
        return json.loads(response.text)['Code']
    cfg_url, cleanup_config_url_content, register_to_config_url = config_url(ocp_config_server, appname, cid)
    ret = post(register_to_config_url)
    if ret != 200:
        if not force_delete:
            raise Exception('%s may have been registered in %s' % (appname, ocp_config_server))
        ret = post(cleanup_config_url_content)
        if ret != 200 :
            raise Exception('failed to clean up the config url content, return code %s' % ret)
        if post(register_to_config_url) != 200:
            return False
    return cfg_url

def configserver_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    options = plugin_context.options
    global_config = cluster_config.get_global_conf()
    appname = global_config['appname'] if 'appname' in global_config else None
    cluster_id = global_config['cluster_id'] if 'cluster_id' in global_config else None
    obconfig_url = global_config['obconfig_url'] if 'obconfig_url' in global_config else None
    cfg_url = ''
    if obconfig_url:
        if not appname or not cluster_id:
            stdio.error('need appname and cluster_id')
            return
        cfg_url = get_ob_configserver_cfg_url(obconfig_url, appname, stdio)
        if not cfg_url:
            try:
                cfg_url = init_config_server(obconfig_url, appname, cluster_id, getattr(options, 'force_delete', False), stdio)
                if not cfg_url:
                    stdio.warn(EC_OBSERVER_FAILED_TO_REGISTER_WITH_DETAILS.format(appname, obconfig_url))
            except:
                stdio.warn(EC_OBSERVER_FAILED_TO_REGISTER.format())
    elif 'ob-configserver' in cluster_config.depends and appname:
        obc_cluster_config = cluster_config.get_depend_config('ob-configserver')
        vip_address = obc_cluster_config.get('vip_address')
        if vip_address:
            obc_ip = vip_address
            obc_port = obc_cluster_config.get('vip_port')
        else:
            server = cluster_config.get_depend_servers('ob-configserver')[0]
            client = clients[server]
            obc_ip = NetUtil.get_host_ip() if client.is_localhost() else server.ip
            obc_port = obc_cluster_config.get('listen_port')
        cfg_url = "http://{0}:{1}/services?Action=ObRootServiceInfo&ObCluster={2}".format(obc_ip, obc_port, appname)
    plugin_context.set_variable('cfg_url', cfg_url)

    return plugin_context.return_true()
