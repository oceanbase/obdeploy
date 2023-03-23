# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

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

