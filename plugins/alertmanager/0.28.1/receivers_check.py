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

ALERTMANAGER_NOTICE = {
    'discord': ['webhook_url'],
    'email': ['to', 'smarthost', 'auth_username', 'auth_password', 'from'],
    'msteams': ['webhook_url'],
    'msteamsv2': ['webhook_url'],
    'jira': ['api_url', 'project'],
    'opsgenie': ['api_key', 'api_url'],
    'pagerduty': ['routing_key', 'service_key', 'url'],
    'pushover': ['user_key', 'token'],
    'rocketchat': ['token', 'token_id'],
    'slack': ['api_url'],
    'sns': ['topic_arn', 'phone_number', 'target_arn'],
    'telegram': ['bot_token', 'chat_id'],
    'victorops': ['api_key', 'routing_key'],
    'webhook': ['url'],
    'wechat': ['api_secret', 'corp_id'],
    'webex': ['room_id']
}

SLACK_API_URL = 'https://slack.com/api/chat.postMessage'


def receivers_check(plugin_context, new_cluster_config=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    cluster_receivers_conf = new_cluster_config.get_receivers_conf() if new_cluster_config else cluster_config.get_receivers_conf()
    stdio = plugin_context.stdio

    if cluster_receivers_conf:
        for receiver_name, receiver_conf in cluster_receivers_conf.items():
            if 'receiver_type' not in receiver_conf:
                stdio.error(f"{receiver_name} notification type must be set")
                return False
            receiver_type = receiver_conf['receiver_type']
            if receiver_type not in ALERTMANAGER_NOTICE.keys():
                stdio.error("%s notification type is currently not supported" % receiver_type)
                return plugin_context.return_false()

            notice_fields = ALERTMANAGER_NOTICE[receiver_type]
            if receiver_type == 'sns':
                for field in notice_fields:
                    if field in receiver_conf:
                        break
                else:
                    stdio.error("When using the %s notification method, must specify a value for the topic_arn or phone_number or target_arn" % receiver_type)
                    return plugin_context.return_false()

            for field in notice_fields:
                if field not in receiver_conf and field.join("_file") not in receiver_conf:
                    stdio.error("When using the %s notification method, the %s field must be passed" % (receiver_type, field))
                    return plugin_context.return_false()
            if receiver_type == 'slack':
                receiver_api_url = receiver_conf.get('api_url')
                receiver_api_url = receiver_api_url.replace(" ", "").rstrip("/")
                if receiver_api_url == SLACK_API_URL:
                    for other_field in ['channel', 'http_config']:
                        if other_field not in receiver_conf:
                            stdio.error("If using Bot tokens then %s must be set." % other_field)
                            return plugin_context.return_false()

                
    return plugin_context.return_true()
    


