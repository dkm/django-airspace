#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   django-airspace
#   Copyright (C) 2011  Marc Poulhiès
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU Affero General Public License
#   as published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public
#   License along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.


from piston.handler import BaseHandler
from airspace.models import AirSpaces

class AirSpacesHandler(BaseHandler):
    allowed_methods = ( 'GET', )
    model = AirSpaces

    def read(self, request, airspace_ids=None):
        base = AirSpaces.objects
        
        if airspace_ids and len(airspace_ids.split(',')) == 1:
            return base.get(pk=airspace_ids.split(',')[0])
        elif airspace_ids:
            ids = airspace_ids.strip().split(',')
            spaces = []
            for zid in ids:
                z = base.get(pk=zid)
                spaces.append(z)
            return spaces
        else:
            return base.all() # Or base.filter(...)
