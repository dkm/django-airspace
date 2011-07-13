import os
import sys

path = 'XXXXXX'
if path not in sys.path:
    sys.path.append(path)

path = 'YYYYYYY/'
if path not in sys.path:
    sys.path.append(path)


os.environ['DJANGO_SETTINGS_MODULE'] = 'ZZZZZZZZZZZZZZ.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
