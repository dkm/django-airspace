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

from models import AirSpaces

from tastypie.resources import Resource, ModelResource
from tastypie.fields import ApiField, DictField, CharField, IntegerField
from tastypie.utils import trailing_slash

from django.conf.urls.defaults import *
from django.http import Http404
from django.contrib.gis.measure import Distance, D
from django.contrib.gis.geos import Polygon, Point

import re

# for serialization
from django.utils import simplejson
import geojson
from tastypie.serializers import Serializer


def _internal_get_bbox_AS(request, **kwargs):
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
        
    return spaces


class GeoJSONSerializer(Serializer):
    """
    GeoJSON Serializer that wraps geojson add GeoDjango serializers
    for building FeatureCollection when needed. Catches lists of features
    and wraps them in a FeatureCollection before serializing.
    """

    def to_json(self, data, options=None):
        options = options or {}

        try:
            if type(data) == dict and 'objects' in data:
                data = data['objects']
            
            if type(data) == list and data:
                # we may have a *Collection
                t = data[0].obj.__geo_interface__
                
                if "type" in t :
                    if t['type'] == "Feature":
                        # data items are Feature Objects.
                        features = []
                        for f in data:
                            f_dict = f.obj.__geo_interface__
                            features.append(f_dict)
                        s = geojson.FeatureCollection(features)
                    elif t['type'] in ( "Point", "MultiPoint",
                                        "LineString", "MultiLineString",
                                        "Polygon", "MultiPolygon",
                                        "GeometryCollection"):
                        s = geojson.GeometryCollection(data.obj)
            else:
                return super(GeoJSONSerializer, self).to_json(data, options)
            return geojson.dumps(s)
        except Exception as e:
            # fallback to default serialization.
            return super(GeoJSONSerializer, self).to_json(data, options)

    ## this is untested and currently unused.
    # def from_json(self, content):
    #     return geojson.loads(content)

    
class GeometryField(ApiField):
    """
    Custom ApiField for dealing with data from GeometryFields.
    """
    dehydrated_type = 'geometry'
    help_text = 'Geometry data.'
    
    def dehydrate(self, obj):
        return self.convert(super(GeometryField, self).dehydrate(obj))
    
    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        # Get ready-made geojson serialization and then convert it _back_ to a Python object
        # so that Tastypie can serialize it as part of the bundle
        return simplejson.loads(value.geojson)


class AbstractAirSpacesResource(ModelResource):
    def override_urls(self):
        return [
            # url(r"^(?P<resource_name>%s)/bbox/ids%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_bbox_ids'), name="api_get_bbox_ids"),
            url(r"^(?P<resource_name>%s)/bbox%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_bbox'), name="api_get_bbox"),
            url(r"^(?P<resource_name>%s)/point%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_point'), name="api_get_point"),
            ]

    def get_bbox(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        # onlyids = request.GET.get('onlyids', False)
        
        spaces = _internal_get_bbox_AS(request, **kwargs)

        objects = []
        # if onlyids :
        #     for result in spaces:
        #         objects.append(result.pk)
        # else:
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
        # onlyids = request.GET.get('onlyids', False)

        mq = re.match('(?P<lat>-?[\d\.]+),(?P<lon>-?[\d\.]+)', q)
        mr = re.match('(?P<radius>\d+)', r)

        if not mr:
            radius = 1000
        else:
            radius = int(mr.group('radius'))

        point = Point(float(mq.group('lon')), float(mq.group('lat')))
        
        spaces = AirSpaces.objects.filter(geom__distance_lte=(point, D(m=radius)))

        objects = []

        objects = []
        # if onlyids :
        #     for result in spaces:
        #         objects.append(result.pk)
        # else:
        for result in spaces:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)
            
        self.log_throttled_access(request)
        return self.create_response(request, objects)
    

class AirSpacesResource(AbstractAirSpacesResource):
    geometry = GeometryField(attribute="geom")
    properties = DictField(attribute="get_properties")

    # this default to a feature. Beware when returning multiple objects.
    type = CharField(default="Feature")

    class Meta:
        queryset = AirSpaces.objects.all()
        resource_name = 'airspaces'
        serializer = GeoJSONSerializer()

        # these are wrapped by the 'properties' attribute above.
        excludes = ['name', 'start_date', 'stop_date',
                    'clazz', 'ext_info', 
                    'geom',
                    'ext_info',
                    'ceil_alti', 'ceil_alti_m', 'ceil_fl', 'ceil_ref', 'ceil_f_sfc', 'ceil_unl',
                    'flr_alti', 'flr_alti_m', 'flr_fl', 'flr_ref', 'flr_f_sfc', 'flr_unl' ]


class AirSpacesIDResource(AbstractAirSpacesResource):
    class Meta:
        queryset = AirSpaces.objects.all()
        resource_name = 'airspacesID'

        # these are wrapped by the 'properties' attribute above.
        excludes = ['start_date', 'stop_date',
                    'clazz', 'ext_info', 
                    'geom',
                    'ext_info',
                    'ceil_alti', 'ceil_alti_m', 'ceil_fl', 'ceil_ref', 'ceil_f_sfc', 'ceil_unl',
                    'flr_alti', 'flr_alti_m', 'flr_fl', 'flr_ref', 'flr_f_sfc', 'flr_unl' ]
        
