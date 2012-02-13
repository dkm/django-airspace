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
from tastypie.fields import ApiField, DictField, CharField, IntegerField, ListField
from tastypie.utils import trailing_slash

# for custom Resource
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization

# for returning errors...
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.http import HttpNotFound

from django.conf.urls.defaults import *
from django.contrib.gis.measure import Distance, D
from django.contrib.gis.geos import Polygon, Point, LineString

import os
import re

# for serialization
from django.utils import simplejson
import geojson
from tastypie.serializers import Serializer

from airspace.helpers import interpolate_linestring, get_relief_profile_along_track, get_zone_profile_along_path, merge_touching_linestring, loadFromGpx


def _internal_get_bbox_AS(request, **kwargs):
    q = request.GET.get('q', '').strip()
    m = re.match('(?P<lowlat>-?[\d\.]+),(?P<lowlon>-?[\d\.]+),(?P<highlat>-?[\d\.]+),(?P<highlon>-?[\d\.]+)', q)

    if not m:
        raise ImmediateHttpResponse(response=HttpNotFound())

    lowlat = float(m.group('lowlat'))
    lowlon = float(m.group('lowlon'))
    highlon = float(m.group('highlon'))
    highlat = float(m.group('highlat'))
        
    zone_bbox = Polygon(((float(lowlat),float(lowlon)),
                         (float(lowlat), float(highlon)),
                         (float(highlat), float(highlon)),
                         (float(highlat), float(lowlon)),
                         (float(lowlat), float(lowlon))))

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
            url(r"^(?P<resource_name>%s)/bbox%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_bbox'), name="api_get_bbox"),
            url(r"^(?P<resource_name>%s)/point%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_point'), name="api_get_point"),
            url(r"^(?P<resource_name>%s)/name%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_name'), name="api_get_name"),
            ]

    def get_bbox(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        spaces = _internal_get_bbox_AS(request, **kwargs)

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

        point = Point(float(mq.group('lat')), float(mq.group('lon')))
        
        spaces = AirSpaces.objects.filter(geom__distance_lte=(point, D(m=radius)))

        objects = []
        for result in spaces:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)
            
        self.log_throttled_access(request)
        return self.create_response(request, objects)

    def get_name(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        q = request.GET.get('q', '').strip()
        spaces = AirSpaces.objects.filter(name__icontains=q)

        objects = []
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
        allowed_methods = ['get']

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
        allowed_methods = ['get']

        # these are wrapped by the 'properties' attribute above.
        excludes = ['start_date', 'stop_date',
                    'clazz', 'ext_info', 
                    'geom',
                    'ext_info',
                    'ceil_alti', 'ceil_alti_m', 'ceil_fl', 'ceil_ref', 'ceil_f_sfc', 'ceil_unl',
                    'flr_alti', 'flr_alti_m', 'flr_fl', 'flr_ref', 'flr_f_sfc', 'flr_unl' ]
        

##
## Intersection handling
##

def get_space_intersect_path(path, height_limit=None):
    spaces = AirSpaces.objects.filter(geom__intersects=path)
    bundle = IntersectionBundle()

    for iz in spaces:
        intersect = path.intersection(iz.geom)
        
        if intersect.geom_typeid == 1: ## LineString
            intersects = [intersect]
        elif intersect.geom_typeid == 5: ## MultiLineString
            intersects =  merge_touching_linestring(intersect)

        for ls in intersects:
            floor, ceiling, minh, maxh = get_zone_profile_along_path(iz, ls)

            if len(ls[0]) == 3:
                # 0: looking for start
                # 1: building segment
                state = 0
                intersect_ls = []

                if not height_limit or minh < height_limit:
                    bundle.airspaces_id.add(iz.pk)
                    
                for i,p in enumerate(ls):
                    inside_zone = floor[i] < p and p < ceiling[i]

                    if state == 0:
                        if inside_zone:
                            state = 1
                            intersect_ls.append(p)
                    elif state == 1:
                        if inside_zone:
                            intersect_ls.append(p)
                        else:
                            state = 0
                            
                            i = Intersection(iz.pk, ls, ceiling, floor, minh, maxh, [path.project(Point(x)) for x in intersect_ls])
                            bundle.intersections.append(i)
                            intersect_ls = []
            else:
                if not height_limit or minh < height_limit:
                    bundle.airspaces_id.add(iz.pk)
                
                    i = Intersection(iz.pk, ls, ceiling, floor, minh, maxh, [path.project(Point(x)) for x in ls])
                
                    bundle.intersections.append(i)
        
    return bundle

class Intersection:
    def __init__(self, airspace_id, intersection_seg, data_top, data_bottom, minh, maxh, indexes):
        self.airspace_id = airspace_id # airspace being intersected
        self.intersection_seg = intersection_seg # linestring intersection
        self.data_top = data_top # floor for airspace along intersection
        self.data_bottom = data_bottom # ceiling for airspace along intersection
        self.minh = minh # minimum height of airspace along intersection
        self.maxh = maxh # maximim height of airspace along intersection
        self.indexes = indexes # indexes for linestring intersection


    def as_dict(self):
        r = {
            'airspace_id' : self.airspace_id,
            'intersection_seg' : simplejson.loads(self.intersection_seg.geojson),
            'data_top' : self.data_top,
            'data_bottom' : self.data_bottom,
            'minh' : self.minh,
            'maxh' : self.maxh,
            'indexes' : self.indexes,
            }
        return r
        
class IntersectionBundle:
    def __init__(self):
        self.airspaces_id = set() # list of IDs of airspace intersected. Could be omitted.
        self.intersections = [] # contains Intersection objects
        self.indexes = None # could be removed ?
        self.interpolated = None # interpolated version of path sent by user
        self.relief_profile = None # relief along path, using interpolated version.
    

class IntersectionsResource(Resource):
    airspaces_id = ListField(attribute='airspaces_id') # list of IDs of airspace intersected. Could be omitted.
    intersections = ListField(attribute='intersections') # contains Intersection objects
    indexes = ListField(attribute='indexes') # could be removed ?
    interpolated = ListField(attribute='interpolated') # interpolated version of path sent by user
    relief_profile = ListField(attribute='relief_profile') # relief along path, using interpolated version.

    class Meta:
        resource_name = 'intersections'
        object_class = IntersectionBundle
        authentication = Authentication()
        authorization = Authorization()
        allowed_methods = ['get']
        include_resource_uri = False

    def base_urls(self):
        return [ url(r"^(?P<resource_name>%s)/path%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_path'), name="api_get_path"),
                 url(r"^(?P<resource_name>%s)/gpx/(?P<gpxid>.*)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_gpx'), name="api_get_gpx"),]

    def get_path(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        q = request.GET.get('q', '').strip().split(',')
        coords = []
        for p in q:
            mq = re.match('(?P<lat>-?[\d\.]+) (?P<lon>-?[\d\.]+)', p)
            coords.append([float(mq.group('lat')), float(mq.group('lon'))])

        h = request.GET.get('h', None)
        try:
            h = float(h)
        except:
            h = None
        
        path = LineString(coords)
        indexes, interpolated = interpolate_linestring(path)
        relief_profile = get_relief_profile_along_track(interpolated)
        
        ib = get_space_intersect_path(LineString(interpolated), h)
        ib.indexes = indexes
        ib.interpolated = interpolated
        ib.relief_profile = relief_profile
        
        bundle = self.build_bundle(obj=ib, request=request)
        bundle = self.full_dehydrate(bundle)

        self.log_throttled_access(request)
        return self.create_response(request, bundle)

    def get_gpx(self, request, **kwargs):
        try:
            filename = kwargs.get('gpxid', None)
            dfilename = os.path.join("uploads", filename)
        
            track_geos = loadFromGpx(str(dfilename))
            relief_profile = get_relief_profile_along_track(track_geos)
        except:
            raise ImmediateHttpResponse(response=HttpNotFound())
        
        ib = get_space_intersect_path(track_geos)

        ib.indexes = [track_geos.project(Point(x)) for x in track_geos]
        ib.interpolated = []

        ib.relief_profile = relief_profile
                
        bundle = self.build_bundle(obj=ib, request=request)
        bundle = self.full_dehydrate(bundle)
        bundle.data['success'] = True
        bundle.data['trackURL'] = '/static/' + filename
        
        self.log_throttled_access(request)
        return self.create_response(request, bundle)

    def dehydrate_intersections(self, bundle):
        return [x.as_dict() for x in bundle.obj.intersections]
