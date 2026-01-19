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


from singleton_decorator import singleton
from service.handler.base_handler import BaseHandler
from service.handler.rsa_handler import RSAHandler


@singleton
class ConnectHandler(BaseHandler):
    def connect_influxdb(self, host, port, user, password):
        password = RSAHandler().decrypt_private_key(password)
        from influxdb import InfluxDBClient
        client = InfluxDBClient(host=host, port=port, username=user, password=password)
        try:
            client.ping()
            return {"check_result": True}
        except Exception as e:
            self.obd._call_stdio('error', e)
            return {"check_result": False}