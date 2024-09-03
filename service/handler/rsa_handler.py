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

from singleton_decorator import singleton
from service.handler.base_handler import BaseHandler
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
import base64


@singleton
class RSAHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.private_key = RSA.generate(2048)
        self.public_key = self.private_key.public_key()

    def public_key_to_bytes(self):
        try:
            pem_public_key = self.public_key.export_key(format='PEM')
            return pem_public_key, None
        except ValueError as e:
            return None, e

    def decrypt_private_key(self, text):
        try:
            encrypt_data = base64.b64decode(text)
            cipher = PKCS1_v1_5.new(self.private_key)
            decrypt_data = cipher.decrypt(encrypt_data, None)
            return decrypt_data.decode('utf-8')
        except (ValueError, TypeError) as e:
            self.obd.stdio.error("password  decrypt failed, reason: %s" % e)
            raise Exception('rsa decryption an exception occurred: %s' % e)
