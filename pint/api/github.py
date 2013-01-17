# -*- encoding: utf-8 -*-
import codecs
import json
import http
import re
import urllib.parse # Python 3.3

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

    def _use_error_callback(callback, response, decoded_body):
        if not callback:
            return

        data = {
            'code': response.code,
            'body': decoded_body
        }

        if response.error:
            data['error'] = response.error

        error_callback(**data)

    def _decode_response_body(response):
        """ Decodes the JSON-format response body

        :param response: the response object
        :type response: tornado.httpclient.HTTPResponse

        :return: the decoded data
        """
        # Fix GitHub response.
        body = codecs.decode(response.body, 'ascii')
        body = re.sub('"', '\"', body)
        body = re.sub("'", '"', body)
        body = json.loads(body)

        if response.error:
            return None

        return body

    def do(self, uri, token, method='GET', params={}):
        payload = urllib.parse.urlencode(params)

        arguments = {
            'method':  method,
            'url':     '{}?access_token={}'.format(uri, token),
            'headers': self._default_headers,
            'body':    payload
        }

        self._http.request(**arguments)

        response = self._http.getresponse()

        return response.read()



