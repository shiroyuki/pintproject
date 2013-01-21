# -*- encoding: utf-8 -*-
import codecs
import json
import http
import re
import urllib.parse # Python 3.3
from tori.bundle.common.handler import Controller
from tori.db.document import BaseDocument
from tornado.web import asynchronous
from pint.mixin import GitHubMixin
from pint.util import TimeLength

class RequestDeniedError(Exception): pass

class AuthenticationController(Controller, GitHubMixin):
    xsite_token   = 'qwp48fucp89q32'

    def __init__(self, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)

        github_api = self.component('api.github')

        self.client_id     = github_api.id
        self.client_secret = github_api.secret

    @asynchronous
    def get(self):
        params = {
            'redirect_uri': '',
            'client_id':    self.client_id,
            'state':        self.xsite_token
        }

        if self.session.get('user'):
            return self.redirect('/')

        code = self.get_argument('code', None)

        # Seek the authorization
        if code:
            # For security reason, the state value (cross-site token) will be
            # retrieved from the query string.
            params.update({
                'client_secret': self.client_secret,
                'success_callback': self._on_login,
                'error_callback': self._on_error,
                'code':  code,
                'state': self.get_argument('state', None)
            })

            self.get_authenticated_user(**params)

            return

        # Redirect for user authentication
        self.get_authenticated_user(**params)

    def _on_login(self, user, access_token=None):
        self.session.set('user', User(user))
        self.session.set('access_token', access_token)

        self.redirect('/')

    def _on_error(self, code, body=None, error=None):
        self.write('<h1>HTTP {}</h1>'.format(code))

        if body:
            self.write('<p>Content: {}</p>'.format(body))

        if error:
            self.write('<p>Error: {}</p>'.format(error))

        self.finish()

class DataStructure(BaseDocument):
    def __init__(self, data):
        property_map = {}

        for key in self._accepted_keys():
            if key not in data:
                continue

            property_map[key] = data[key]

        super(DataStructure, self).__init__(**property_map)

    def _accepted_keys(self):
        raise NotImplemented()

class Tag(DataStructure):
    def _accepted_keys(self):
        return ['name', 'tarball_url', 'zipball_url']

class Branch(DataStructure):
    def _accepted_keys(self):
        return ['name']

class User(DataStructure):
    def _accepted_keys(self):
        # 'name' is only available for the session owner.
        return ['name', 'login', 'avatar_url']

class Repository(BaseDocument):
    __accepted_keys__   = [
        'name', 'language', 'clone_url', 'id', 'created_at',
        'updated_at', 'branches_url', 'tags_url', 'private',
        'fork'
    ]
    __request_uri_map__ = {}

    def __init__(self, data, api, token=None):
        self._last_update = None
        self._tags  = {}
        self._age   = None
        self._api   = api
        self._token = token

        property_map = {}

        for key in self.__accepted_keys__:
            if key not in data:
                continue

            property_map[key] = data[key]

        self.owner = User(data['owner'])

        super(Repository, self).__init__(**property_map)

    def request_uri(self, url):
        if url not in self.__request_uri_map__:
            self.__request_uri_map__[url] = re.sub('.+{}/'.format(RestAPI._api_url), '/', url)

        return self.__request_uri_map__[url]

    @property
    def branches(self):
        uri = '/repos/{}/{}/branches'.format(self.owner.login, self.name)

        raw_branches = self._api.do(uri)

        branches = []

        for raw_branch in raw_branches:
            branches.append(Branch(raw_branch))

        return branches

    @property
    def tags(self):
        uri = '/repos/{}/{}/tags'.format(self.owner.login, self.name)

        raw_tags = self._api.do(uri)

        tags = []

        for raw_tag in raw_tags:
            tags.append(Tag(raw_tag))

        return tags

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
    def page_url(self):
        return '/{}/{}'.format(self.owner.login, self.name)

class RestAPI(object):
    _default_headers = {'Accept': 'application/json'}
    _api_url         = 'api.github.com'
    _api_port        = 443
    _cache_map       = {}

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

    def repository(self, user_name, repo_name):
        raw_repository = self.do('/repos/{}/{}'.format(user_name, repo_name))

        return Repository(raw_repository, self)

    def repositories(self, user_name):
        repositories      = []
        raw_reponsitories = self.do('/users/{}/repos'.format(user_name))

        for raw_reponsitory in raw_reponsitories:
            repositories.append(Repository(raw_reponsitory, self))

        return repositories

    def do(self, uri, token=None, method='GET', params={}):
        payload    = urllib.parse.urlencode(params)
        actual_uri = '{}?access_token={}'.format(uri, token) if token else uri

        arguments = {
            'method':  method,
            'url':     actual_uri,
            'headers': self._default_headers,
            'body':    payload
        }

        if method.lower() == 'get' and actual_uri in self._cache_map:
            return self._cache_map[actual_uri]

        try:
            self._http.request(**arguments)
        except http.client.CannotSendRequest:
            raise RequestDeniedError()

        try:
            response = self._http.getresponse()
        except http.client.BadStatusLine:
            return None

        self._cache_map[actual_uri] = self._decode_response_body(response.read())

        return self._cache_map[actual_uri]



