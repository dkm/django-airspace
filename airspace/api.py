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

from tastypie.resources import ModelResource
from models import AirSpaces
from django.conf.urls.defaults import *
from tastypie.utils import trailing_slash
from django.http import Http404

from django.contrib.gis.measure import Distance, D
from django.contrib.gis.geos import Polygon, Point
import re

class AirSpacesResource(ModelResource):
    class Meta:
        queryset = AirSpaces.objects.all()
        resource_name = 'airspaces'

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/bbox%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_bbox'), name="api_get_bbox"),
            url(r"^(?P<resource_name>%s)/point%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_point'), name="api_get_point"),
            ]

    def get_bbox(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        q = request.GET.get('q', '').strip()

        m = re.match('(?P<lowlat>-?[\d\.]+),(?P<lowlon>-?[\d\.]+),(?P<highlat>-?[\d\.]+),(?P<highlon>-?[\d\.]+)', q)

        if not m:
            raise Http404("Sorry, no results on that page.")

        lowlat = float(m.group('lowlat'))
        lowlon = float(m.group('lowlon'))
        highlon = float(m.group('highlon'))
        highlat = float(m.group('highlat'))
        
        zone_bbox = Polygon(((lowlon, lowlat),
                             (highlon, lowlat),
                             (highlon, highlat),
                             (lowlon, highlat),
                             (lowlon, lowlat)))

        spaces = AirSpaces.objects.filter(geom__intersects=zone_bbox)

        objects = []
        for result in spaces:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)
            
        self.log_throttled_access(request)
        return self.create_response(request, objects)

    def get_point(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        q = request.GET.get('q', '').strip()
        r = request.GET.get('r', '').strip()
        
        mq = re.match('(?P<lat>-?[\d\.]+),(?P<lon>-?[\d\.]+)', q)
        mr = re.match('(?P<radius>\d+)', r)

        if not mr:
            radius = 1000
        else:
            radius = int(mr.group('radius'))

        point = Point(float(mq.group('lon')), float(mq.group('lat')))
        
        spaces = AirSpaces.objects.filter(geom__distance_lte=(point, D(m=radius)))

        objects = []
        for result in spaces:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)
            
        self.log_throttled_access(request)
        return self.create_response(request, objects)
