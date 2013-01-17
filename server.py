# -*- coding: utf-8 -*-
import sys

if ('2.7' < sys.version_info < '2.8') or (sys.version_info < '3.3'):
    print('This application requires Python 2.7.x, 3.3 or higher.')

    sys.exit()

from tori.application import Application
from fixtures import auto_load_mongodb

application = Application('config/app.xml')

auto_load_mongodb()

application.start()
