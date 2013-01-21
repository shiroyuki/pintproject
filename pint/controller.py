# -*- coding: utf-8 -*-
from tori.decorator.controller  import renderer
from tori.bundle.common.handler import Controller
from pint.api.github import RequestDeniedError

@renderer('pint.view')
class Home(Controller):
    def get(self):
        contexts = {}

        github_api = self.component('api.github')

        if self.authenticated:
            try:
                contexts['repositories'] = github_api.repositories(self.authenticated.login)
            except RequestDeniedError as exception:
                pass

        self.render('index.html', **contexts)

@renderer('pint.view')
class Repository(Controller):
    def get(self, owner, name):
        github_api = self.component('api.github')

        self.render('repository.html', repository=github_api.repository(owner, name))

class Logout(Controller):
    def get(self):
        self.session.delete('user')
        self.session.delete('access_token')
        self.redirect('/')

