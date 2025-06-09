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

def show_license(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    sql = "select * from oceanbase.DBA_OB_LICENSE"
    license = cursor.fetchall(sql, raise_exception=True, exc_level='verbose')
    if not license:
        stdio.error("License information query failed.")
        return plugin_context.return_false()

    stdio.print_list(license, ['end_user', 'license_id', 'license_code', 'license_type', 'product_type',
                    'issuance_date', 'activation_time', 'expired_time', 'options', 'node_num'],
                    lambda x: [x['END_USER'], x['LICENSE_ID'], x['LICENSE_CODE'], x['LICENSE_TYPE'], x['PRODUCT_TYPE'],
                    x['ISSUANCE_DATE'], x['ACTIVATION_TIME'], x['EXPIRED_TIME'], x['OPTIONS'],
                    x['NODE_NUM']], title='license')
    return plugin_context.return_true()