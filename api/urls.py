#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from piston.resource import Resource
from handlers import AirSpacesHandler

airspaces_handler = Resource(AirSpacesHandler)


urlpatterns = patterns('',
   url(r'^airspace/(?P<airspace_ids>\d+(,\d+)*)/', airspaces_handler),
   url(r'^airspace/', airspaces_handler),
)
