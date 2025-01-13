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
