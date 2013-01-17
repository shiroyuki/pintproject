# -*- encoding: utf-8 -*-
import codecs
import json
import http
import math
import re
import urllib.parse # Python 3.3
import time

class RequestDeniedError(Exception): pass

class ImmutableData(object):
    def __init__(self, **kwargs):
        for name in kwargs:
            object.__setattr__(self, name, kwargs[name])

    def __setattr__(self, key, value):
        raise NotImplemented('Disabled')

    def __delattr__(self, item):
        raise NotImplemented('Disabled')

class Repository(object):
    __accepted_keys__   = ['name', 'language', 'clone_url', 'id', 'updated_at', 'tags_url', 'private', 'fork']
    __unit_map__        = [
        ('second', 1),
        ('minute', 60),
        ('hour',   60),
        ('day',    24)
    ]

    def __init__(self, **kwargs):
        property_map = {
            'tags': {}
        }

        for key in self.__accepted_keys__:
            property_map[key] = kwargs[key]

        ImmutableData.__init__(self, **property_map)

    @property
    def time_difference(self):
        last_update = time.mktime(time.strptime(self.updated_at, '%Y-%m-%dT%H:%M:%SZ'))
        current     = time.mktime(time.gmtime())

        return math.floor(current - last_update)

    @property
    def last_update(self):
        time_difference = self.time_difference

        unit_name = None

        print(self.name)

        for name, divider in self.__unit_map__:
            diff = math.floor(time_difference / divider)

            print('{} in {}'.format(diff, name))

            if diff < 1:
                break

            time_difference = diff
            unit_name       = name

        return '{} {}{}'.format(time_difference, unit_name, '' if time_difference == 1 else 's')

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
        except http.client.BadStatusLine:
            raise RequestDeniedError()
        except http.client.CannotSendRequest:
            raise RequestDeniedError()

        response = self._http.getresponse()

        body = self._decode_response_body(response.read())

        return body



