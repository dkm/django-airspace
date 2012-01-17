#!/usr/bin/env python
# -*- coding: utf-8 -*-

from piston.handler import BaseHandler
from airspace.models import AirSpaces

class AirSpacesHandler(BaseHandler):
    allowed_methods = ( 'GET', )
    model = AirSpaces

    def read(self, request, airspace_id=None, airspace_ids=None):
        base = AirSpaces.objects
        
        if airspace_id:
            return base.get(pk=airspace_id)
        elif airspace_ids:
            ids = airspace_ids.strip().split(',')
            spaces = []
            for zid in ids:
                z = base.get(pk=zid)
                spaces.append(z)
            return spaces
        else:
            return base.all() # Or base.filter(...)
