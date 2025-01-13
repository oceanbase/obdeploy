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

import logging.config


DEFAULT_LOGGER="DefaultLogger"


def get_logger_config(file_name="app.log", level="INFO"):
    logger_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'filters': {
                'correlation_id': {
                    '()': 'asgi_correlation_id.CorrelationIdFilter',
                    'uuid_length': 32,
                },
            },
            'formatters': {
                'simple': {
                    'class': 'logging.Formatter',
                    'format': '%(asctime)s %(levelname)s %(funcName)s (%(filename)s:%(lineno)d) [%(correlation_id)s] %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'filters': ['correlation_id'],
                    'formatter': 'simple'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filters': ['correlation_id'],
                    'filename': file_name,
                    'formatter': 'simple'
                }
            },
            'loggers': {
                DEFAULT_LOGGER: {
                    'handlers': ['console', 'file'],
                    'level': level
                }
            }
        }
    return logger_config

def get_logger():
    return logging.getLogger(DEFAULT_LOGGER)

