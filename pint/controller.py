# -*- coding: utf-8 -*-
from tori.controller           import Controller
from tori.decorator.controller import renderer
from tornado.web import asynchronous

from pint.mixin import GitHubMixin

@renderer('pint.view')
class Home(Controller):
    def get(self):
        contexts = {}

        github_api = self.component('api.github')

        if self.session.get('user'):
            contexts['repositories'] = github_api.do(
                '/user/repos',
                self.session.get('access_token')
            )

        self.render('index.html', **contexts)

class Logout(Controller):
    def get(self):
        self.session.delete('user')
        self.session.delete('access_token')
        self.redirect('/')

class GitHubAuthentication(Controller, GitHubMixin):
    xsite_token   = 'qwp48fucp89q32'

    def __init__(self, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)

        github_api = self.component('api.github')

        self.client_id     = github_api.id
        self.client_secret = github_api.secret

    @asynchronous
    def get(self):
        params = {
            'redirect_uri': 'http://pintproject.org:8000/login/github',
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
        self.session.set('user', user)
        self.session.set('access_token', access_token)

        self.redirect('/')

    def _on_error(self, code, body=None, error=None):
        self.write('<h1>HTTP {}</h1>'.format(code))

        if body:
            self.write('<p>Content: {}</p>'.format(body))

        if error:
            self.write('<p>Error: {}</p>'.format(error))

        self.finish()