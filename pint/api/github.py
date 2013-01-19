# -*- encoding: utf-8 -*-
import codecs
import json
import http
import math
import re
import urllib.parse # Python 3.3
import time

from tori.db.document import BaseDocument
from pint.util import TimeLength

class RequestDeniedError(Exception): pass

class Repository(BaseDocument):
    __accepted_keys__ = ['name', 'language', 'clone_url', 'id', 'created_at', 'updated_at', 'tags_url', 'private', 'fork']

    def __init__(self, **kwargs):
        property_map = {
            'tags': {},
            '_last_update': None,
            '_age': None
        }

        for key in self.__accepted_keys__:
            property_map[key] = kwargs[key]

        super(Repository, self).__init__(**property_map)

    @property
    def age(self):
        if not self._age:
            self._age = TimeLength(self.created_at)

        return self._age

    @property
    def last_update(self):
        if not self._last_update:
            self._last_update = TimeLength(self.updated_at)

        return self._last_update

    @property
    def releasable(self):
        return not self.fork and not self.private

class GitHub(object):
    _default_headers = {'Accept': 'application/json'}
    _api_url         = 'api.github.com'
    _api_port        = 443

    def __init__(self, cid, secret):
        self._id     = cid
        self._secret = secret
        self._http   = http.client.HTTPSConnection(self._api_url, self._api_port)

    @property
    def id(self):
        return self._id

    @property
    def secret(self):
        return self._secret

    def _use_error_callback(self, callback, response, decoded_body):
        if not callback:
            return

        data = {
            'code': response.code,
            'body': decoded_body
        }

        if response.error:
            data['error'] = response.error

        callback(**data)

    def _decode_response_body(self, responseBody):
        """ Decodes the JSON-format response body

        :param response: the response object
        :type response: tornado.httpclient.HTTPResponse

        :return: the decoded data
        """
        # Fix GitHub response.
        body = codecs.decode(responseBody, 'ascii')
        body = re.sub('"', '\"', body)
        body = re.sub("'", '"', body)
        body = json.loads(body)

        return body

    def repositories(self, token):
        repositories      = []
        raw_reponsitories = self.do('/user/repos', token)

        for raw_reponsitory in raw_reponsitories:
            repositories.append(Repository(**raw_reponsitory))

        return repositories

    def do(self, uri, token, method='GET', params={}):
        payload = urllib.parse.urlencode(params)

        arguments = {
            'method':  method,
            'url':     '{}?access_token={}'.format(uri, token),
            'headers': self._default_headers,
            'body':    payload
        }

        try:
            self._http.request(**arguments)
        except http.client.CannotSendRequest:
            raise RequestDeniedError()

        try:
            response = self._http.getresponse()
        except http.client.BadStatusLine:
            return None

        body = self._decode_response_body(response.read())

        return body



