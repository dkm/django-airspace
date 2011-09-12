from django.http import HttpResponse
from airspace.models import AirSpaces
from django.shortcuts import render_to_response
from django.template import RequestContext

## for computing zone in a given radius from a point
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance, D

from django.contrib.gis.geos import GEOSGeometry

from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

from django.contrib.gis.geos import LineString,Polygon,MultiLineString
##from django.contrib.gis.geos import Polygon

import geojson
import json

from django.middleware import csrf

from django.http import Http404

from django import forms

import os.path
import re
import osgeo.ogr

import ossim

from django.contrib.gis.geos import GEOSGeometry
    
def loadFromGpx(gpxfilename, detectProjection=True):
    """
    From a GPX, loads all lines/multilines and returns a single
    geos representation (tracks are merged)
    """
    driver = osgeo.ogr.GetDriverByName('GPX')
    dataSource = driver.Open(gpxfilename, 0)

    # merge all track into a single track
    # this can be a problem, depending on why the there is multiple tracks...
    merged_points = []

    for i in xrange(dataSource.GetLayerCount()):
	layer = dataSource.GetLayer(i)
	layer.ResetReading()
	spatialRef = None
	if detectProjection:
            spatialRef = layer.GetSpatialRef()
	# elif useProj4:
	# 	spatialRef = osr.SpatialReference()
	# 	spatialRef.ImportFromProj4(sourceProj4)

            
	if spatialRef == None:	
            # No source proj specified yet? Then default to do no reprojection.
            # Some python magic: skip reprojection
            # altogether by using a dummy lamdba
            # funcion. Otherwise, the lambda will
            # be a call to the OGR reprojection
            # stuff.
            reproject = lambda(geometry): None
	else:
            destSpatialRef = osgeo.osr.SpatialReference()
            destSpatialRef.ImportFromEPSG(4326)	
            # Destionation projection will *always* be EPSG:4326,
            # WGS84 lat-lon
            coordTrans = osgeo.osr.CoordinateTransformation(spatialRef,destSpatialRef)
            reproject = lambda(geometry): geometry.Transform(coordTrans)
        featureDefinition = layer.GetLayerDefn()


	for j in range(layer.GetFeatureCount()):
            feature = layer.GetNextFeature()
            geometry = feature.GetGeometryRef()
            geometryType = geometry.GetGeometryType()
            
            ls = []

            if  geometryType == osgeo.ogr.wkbLineString or geometryType == osgeo.ogr.wkbLineString25D:
                if geometry.GetPointCount() <= 2:
                    continue
                ls.append(geometry)
            elif geometryType == osgeo.ogr.wkbMultiLineString or geometryType == osgeo.ogr.wkbMultiLineString25D:
                for i in xrange(geometry.GetGeometryCount()):
                    subgeom = geometry.GetGeometryRef(i)
                    if subgeom.GetPointCount() <= 2:
                        continue
                    else:
                        ls.append(subgeom)
            
            for line in ls:
                reproject(line)
                for i in xrange(line.GetPointCount()):
                    merged_points.append(line.GetPoint(i))
    
    merged_line = LineString(merged_points)
    return merged_line

### from file-upload w/ django support
### Heavily based on code from http://kuhlit.blogspot.com/2011/04/ajax-file-uploads-and-csrf-in-django-13.html

def save_upload( uploaded, filename, raw_data ):
  ''' 
  raw_data: if True, uploaded is an HttpRequest object with the file being
            the raw post data 
            if False, uploaded has been submitted via the basic form
            submission and is a regular Django UploadedFile in request.FILES
  '''
  try:
    from io import FileIO, BufferedWriter
    with BufferedWriter( FileIO( filename, "wb" ) ) as dest:
      # if the "advanced" upload, read directly from the HTTP request 
      # with the Django 1.3 functionality
      if raw_data:
        foo = uploaded.read( 1024 )
        while foo:
          dest.write( foo )
          foo = uploaded.read( 1024 ) 
      # if not raw, it was a form upload so read in the normal Django chunks fashion
      else:
        for c in uploaded.chunks( ):
          dest.write( c )
      # got through saving the upload, report success
      return True
  except IOError:
    # could not open the file most likely
    pass
  return False

# this one can be used to get error when making an Ajax call...
# def json_track_upload(request):
#     try:
#         return json_track_upload__(request)
#     except:
#         import traceback
#         import sys
#         exc_info = sys.exc_info()
#         print "######################## Exception #############################"
#         print '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
#         print "################################################################"
    


def get_relief_profile_along_track(track):
    """
    track should be a list of coord.
    """
    ossim.init('XXX/ossim_preferences_template')

    relief_profile = []
    # pnt = GEOSGeometry(track)
    for p in track:
        h = ossim.height(p[1], p[0])
            ## if data not available, default to 0
        if h:
            relief_profile.append(h[1])
        else:
            relief_profile.append(0)
    
    return relief_profile


def get_spec_alt(spec, point):
    c = None
    try:
        if 'flevel' in spec:
            c = int(spec['flevel']) * 100 * 0.3048

        elif 'ref' in spec:
            if spec['ref'] == 'AMSL':
                c = int(spec['basealti'])
            elif spec['ref'] == 'AGL':
                h = ossim.height(point[1], point[0])
                c = h[1] + spec['basealti']
            elif spec['ref'] == 'SFC':
                h = ossim.height(point[1], point[0])
                c = h[1]
        if c == None:
            print "Error :", spec
    except:
        # most probably, not possible to get ground height...
        pass
    return c

def get_ceiling_floor_at_point(airspace, point):
    ceil,floor = None, None

    ceil_specs = json.loads(airspace.ceiling)
    floor_specs = json.loads(airspace.floor)

    for spec in ceil_specs:
        c = get_spec_alt(spec, point)
        if ceil == None:
            ceil = c
        else:
            ceil = max(ceil, c)
            
    for spec in floor_specs:
        c = get_spec_alt(spec, point)
        if floor == None:
            floor = c
        else:
            floor = min(floor, c)
    
    return (ceil,floor)

def get_zone_profile_along_path(airspace, path):
    floor = []
    ceiling = []

    for point in path:
        c,f = get_ceiling_floor_at_point(airspace, point)
        floor.append(f)
        ceiling.append(c)

    return (floor, ceiling)

def get_start_stop_segement_in_path(path, segment, thr=0):
    start = stop = None
    
    for i,p in enumerate(path):
        if not start and segment[0][0] == p[0] and segment[0][1] == p[1] :
            start = i
        elif start and not stop and segment[-1][0] == p[0] and segment[-1][1] == p[1] :
            stop = i

        if start and stop:
            break

    if thr != 0 :
        startp = stopp = None
        if not start:
            startp = Point(segment[0])
        if not stop:
            stopp = Point(segment[-1])
            
        for i,p in enumerate(path):
            if not start:
                print 'dist start:', startp.distance(Point(p)) 
            if not stop:
                print 'dist sttop:', stopp.distance(Point(p)) 

            if start and not stop and stopp.distance(Point(p)) <= thr:
                stop = i
            if not start and startp.distance(Point(p)) <= thr:
                start = i
    
    return (start,stop)

#yes, this one is very sub-sub-optimal...
# def get_index_of_point_along_path(path, point, thr = 0, after=-1):
#     for i,p in enumerate(path):
#         if point[0] == p[0] and point[1] == p[1] and i>after:
#             return i
        
#     if thr != 0:
#         pt = Point(point)
#         for i,p in enumerate(path):
#             if pt.distance(Point(p)) <= thr:
#                 return i
#     return -1

def merge(ML):
    coords = list(ML[0])
    for ls in ML[1:-1]:
        coords += list(ls)[1:-1]
    coords += list(ML[-1][1:])
    return LineString(coords)

def merge_touching_linestring(multiLS):
    buf = [multiLS[0]]
    final = []
    
    for i,ls in enumerate(multiLS[1:]):
        prev_p = buf[-1][-1]
        next_p = ls[0]
        if prev_p[0] == next_p[0] and prev_p[1] == next_p[1]:
            buf.append(ls)
        else:
            ml = MultiLineString(buf)
            final.append(merge(ml))
            buf = [ls]
    if len(buf) > 2:
        ml = MultiLineString(buf)

        final.append(merge(ml))
    else:
        final.append(buf[0])
    return final
    

def get_space_intersect_path(path):
    spaces = AirSpaces.objects.filter(geom__intersects=path)

    data = serializers.serialize('json', spaces, fields=[])
    inters = []

    for iz in spaces:
        intersect = path.intersection(iz.geom)
       
        if intersect.geom_typeid == 1: ## LineString
            nls = intersect
            
            floor, ceiling = get_zone_profile_along_path(iz, nls)
            
            inters.append({
                'zid' : iz.pk,
                'inter': json.loads(nls.json),
                'data_top' : floor,
                'data_bottom': ceiling,
                'indexes' : [path.project(Point(x)) for x in nls],
                })
        elif intersect.geom_typeid == 5: ## MultiLineString
            intersect_merged = merge_touching_linestring(intersect)

            for ls in intersect_merged:
                nls = ls
                floor, ceiling = get_zone_profile_along_path(iz, nls)

                inters.append({
                    'zid' : iz.pk,
                    'inter': json.loads(nls.json),
                    'data_top' : floor,
                    'data_bottom': ceiling,
                    'indexes' : [path.project(Point(x)) for x in nls],
                    })
        
    return (data, inters)

## disable CSRF when debugging can help...
##@csrf_exempt
def json_track_upload( request ):
  if request.method == "POST":
    if request.is_ajax( ):
      # the file is stored raw in the request
      upload = request
      is_raw = True
      # AJAX Upload will pass the filename in the querystring if it is the "advanced" ajax upload
      try:
        filename = request.GET[ 'qqfile' ]
      except KeyError: 
        return HttpResponseBadRequest( "AJAX request not valid" )
    # not an ajax upload, so it was the "basic" iframe version with submission via form
    else:
      is_raw = False
      if len( request.FILES ) == 1:
        # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
        # ID based on a random number, so it cannot be guessed here in the code.
        # Rather than editing Ajax Upload to pass the ID in the querystring,
        # observer that each upload is a separate request,
        # so FILES should only have one entry.
        # Thus, we can just grab the first (and only) value in the dict.
        upload = request.FILES.values( )[ 0 ]
      else:
        raise Http404( "Bad Upload" )
      filename = upload.name

    dfilename = os.path.join("uploads", filename)
    
    # save the file
    success = save_upload( upload, dfilename, is_raw )

    ## the str() is needed to make a copy. If not, ogr Driver ctor
    ## panics on the 'const char *' that it receives...
    track_geos = loadFromGpx(str(dfilename))

    inter_space_ids, intersections = get_space_intersect_path(track_geos)

    relief_profile = get_relief_profile_along_track(track_geos)

    # let Ajax Upload know whether we saved it or not by using success: smth
    ##
    ## FIXME this json.loads is not very clean. Serializing and deserializing right after... :(
    ##
    ## use upload.name and not the filename as Django handles static files itself. We should
    ## use some var to get the STATIC root instead of 'static/' !
    ret_json = { 'success': success,
                 'ZID' : json.loads(inter_space_ids),
                 'intersections' : intersections,
                 'relief_profile': relief_profile,
                 'indexes' : [track_geos.project(Point(x)) for x in track_geos],
                 'trackURL': '/static/' + filename }
    
    r = geojson.dumps( ret_json )

    return HttpResponse(r, mimetype='application/json' )

### Heavily based on code from http://kuhlit.blogspot.com/2011/04/ajax-file-uploads-and-csrf-in-django-13.html
### end of file-upload w/ django support

def json_path_id_post(request):
    args = request.POST
    ls = []
    # take only first linestring...
    str_path = args.getlist("LS")[0]
    path = GEOSGeometry(str_path)

    interpolated_path = []
    prev_p = Point(path[0])
    interpolated_path.append(path[0])

    sampling_step = 0.002
    ## sampling = 0.002 (~100m)
    for p in path[1:]:
        n_p = Point(p)
        d = prev_p.distance(n_p)
        if d > sampling_step:
            start_idx = path.project(prev_p)
            nsamples = int(d/sampling_step)
            for i in xrange(nsamples):
                idx = start_idx + sampling_step + i*sampling_step
                interpolated_path.append(list(path.interpolate(idx)))
        prev_p = n_p                      
        interpolated_path.append(p)

    indexes = [path.project(Point(x)) for x in interpolated_path]

    inter_space_ids, intersections = get_space_intersect_path(LineString(interpolated_path))
    relief_profile = get_relief_profile_along_track(interpolated_path)
    
    ret_json = {
        'ZID' : json.loads(inter_space_ids),
        'intersections' :intersections,
        'indexes': indexes,
        'interpolated' : geojson.geometry.LineString(interpolated_path),
        'relief_profile': relief_profile,
        }
    
    r = geojson.dumps( ret_json )
    return HttpResponse(r, mimetype='application/json' )

##
# get a FeatureCollection out of a list of zone id
# Can be via GET or POST

# disable csrf protection 
#@csrf_exempt
def json_zone_post(request):
    args = request.POST
    zones = []
    for i in args.getlist("ZID"):
        zones += i.split(',')
    return internal_json_zones(zones)

def json_zones(request, zone_ids):
    zs = zone_ids.split(',')
    return internal_json_zones(zs)

def internal_json_zones(zone_list):
    try:
        spaces = []
        for zid in zone_list:
            z = AirSpaces.objects.get(pk=zid)
            spaces.append(z)

        js_spaces = geojson.FeatureCollection(spaces)
        s = geojson.dumps(js_spaces)

    except AirSpaces.DoesNotExist:
        raise Http404
    
    return HttpResponse(s, mimetype='application/json')


def json_zones_by_name(request, name):
    try:
        zones = AirSpaces.objects.filter(name__icontains=name)

        data = serializers.serialize('json', zones, fields=[])
        return HttpResponse(data, mimetype='application/json')

        # js_spaces = geojson.FeatureCollection(list(zones))
        # s = geojson.dumps(js_spaces)
        # return HttpResponse(s, mimetype='application/json')
    except AirSpaces.DoesNotExist:
        raise Http404
    
def json_zone(request, zone_id):
    try:
        z = AirSpaces.objects.get(pk=zone_id)
        s = geojson.dumps(z)
    except AirSpaces.DoesNotExist:
        raise Http404
    return HttpResponse(s, mimetype='application/json')


def json_zone_bbox(request, lowlat, lowlon, highlat, highlon):
    zone_bbox = Polygon(((float(lowlat),float(lowlon)),
                         (float(lowlat), float(highlon)),
                         (float(highlat), float(highlon)),
                         (float(highlat), float(lowlon)),
                         (float(lowlat), float(lowlon))))
    spaces = AirSpaces.objects.filter(geom__intersects=zone_bbox)
    js_spaces = geojson.FeatureCollection(list(spaces))

    return HttpResponse(geojson.dumps(js_spaces), mimetype='application/json')

def jsonID_zone_bbox(request, lowlat, lowlon, highlat, highlon):
    zone_bbox = Polygon(((float(lowlat),float(lowlon)),
                         (float(lowlat), float(highlon)),
                         (float(highlat), float(highlon)),
                         (float(highlat), float(lowlon)),
                         (float(lowlat), float(lowlon))))
    spaces = AirSpaces.objects.filter(geom__intersects=zone_bbox)

    data = serializers.serialize('json', spaces, fields=[])

    return HttpResponse(data, mimetype='application/json')


def jsonID_zone_point(request, lat, lon, radius):
    point = Point(float(lat), float(lon))
    spaces = AirSpaces.objects.filter(geom__distance_lte=(point, D(m=int(radius))))

    data = serializers.serialize('json', spaces, fields=[])
    return HttpResponse(data, mimetype='application/json')


def amap(request):
    ctx = RequestContext( request, {
         'csrf_token': csrf.get_token( request ),
         } )
    
    all_as = AirSpaces.objects.all()
    return render_to_response('airspace/amap.html',
                              {'as_list' : all_as},
                              context_instance=ctx)
