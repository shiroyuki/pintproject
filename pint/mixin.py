import codecs
import json
import re
import urllib

from tornado import httpclient
from tornado.auth import OAuth2Mixin

class GitHubMixin(OAuth2Mixin):
    """GitHub OAuth2 Authentication

    To authenticate with GitHub, first register your application at
    https://github.com/settings/applications/new to get the client ID and
    secret.
    """

    _API_BASE_HEADERS = {'Accept': 'application/json'}
    _OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    _OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
    _OAUTH_USER_URL = 'https://api.github.com/user?access_token='

    def get_authenticated_user(self, redirect_uri, client_id, state,
                               client_secret=None, code=None,
                               success_callback=None,
                               error_callback=None):
        """ Fetches the authenticated user

        :param redirect_uri: the redirect URI
        :param client_id: the client ID
        :param state: the unguessable random string to protect against
                      cross-site request forgery attacks
        :param client_secret: the client secret
        :param code: the response code from the server
        :param success_callback: the success callback used when fetching
                                 the access token succeeds
        :param error_callback: the callback used when fetching the access
                               token fails
        """
        if code:
            self._fetch_access_token(
                code,
                success_callback,
                error_callback,
                redirect_uri,
                client_id,
                client_secret,
                state
            )

            return

        params = {
            'redirect_uri': redirect_uri,
            'client_id':    client_id,
            'extra_params': {
                'state': state
            }
        }

        self.authorize_redirect(**params)

    def _fetch_access_token(self, code, success_callback, error_callback,
                           redirect_uri, client_id, client_secret, state):
        """ Fetches the access token.

        :param code: the response code from the server
        :param success_callback: the success callback used when fetching
                                 the access token succeeds
        :param error_callback: the callback used when fetching the access
                               token fails
        :param redirect_uri: the redirect URI
        :param client_id: the client ID
        :param client_secret: the client secret
        :param state: the unguessable random string to protect against
                      cross-site request forgery attacks
        :return:
        """
        if not (client_secret and success_callback and error_callback):
            raise ValueError('The client secret or any callbacks are undefined.')

        params = {
            'code':          code,
            'redirect_url':  redirect_uri,
            'client_id':     client_id,
            'client_secret': client_secret,
            'state':         state
        }

        http = httpclient.AsyncHTTPClient()

        callback_share_data = {}

        def use_error_callback(response, decoded_body):
            data = {
                'code': response.code,
                'body': decoded_body
            }

            if response.error:
                data['error'] = response.error

            error_callback(**data)

        def decode_response_body(response):
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
                use_error_callback(response, body)

                return None

            return body

        def on_authenticate(response):
            """ The callback handling the authentication

            :param response: the response object
            :type response: tornado.httpclient.HTTPResponse
            """
            body = decode_response_body(response)

            if not body:
                return

            if 'access_token' not in body:
                use_error_callback(response, body)

                return

            callback_share_data['access_token'] = body['access_token']

            http.fetch(
                '{}{}'.format(self._OAUTH_USER_URL, callback_share_data['access_token']),
                on_fetching_user_information,
                headers=self._API_BASE_HEADERS
            )

        def on_fetching_user_information(response):
            """ The callback handling the data after fetching the user info

            :param response: the response object
            :type response: tornado.httpclient.HTTPResponse
            """
            # Fix GitHub response.
            user = decode_response_body(response)

            if not user:
                return

            success_callback(user, callback_share_data['access_token'])

        try:
            # Python 2.6
            body = urllib.urlencode(params)
        except AttributeError:
            # Python 3.3
            body = urllib.parse.urlencode(params)

        # Request the access token.
        http.fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            on_authenticate,
            method='POST',
            body=body,
            headers=self._API_BASE_HEADERS
        )