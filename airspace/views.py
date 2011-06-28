from django.http import HttpResponse
from airspace.models import AirSpaces
from django.shortcuts import render_to_response
from django.template import RequestContext

from django import forms

from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

from django.contrib.gis.geos import Polygon
import geojson

from django.middleware import csrf

from django.http import Http404

from django import forms

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
     
    # save the file
    success = save_upload( upload, filename, is_raw )

    # interlist = ##Something that computes the intersections##
    # for debug, simply take some zones around Grenoble to check the machinery :)
    interlist = [47,48,278,281,287,288,289,295,296,307,308,313,607,
                 894,895,963,964,966,1008,1011,1012,1113,1171,1187,1188,1189,1190,1191]
 
    # let Ajax Upload know whether we saved it or not
    import json
    ret_json = { 'success': success, 'ZID' : interlist }
    return HttpResponse( json.dumps( ret_json ) )

### Heavily based on code from http://kuhlit.blogspot.com/2011/04/ajax-file-uploads-and-csrf-in-django-13.html
### end of file-upload w/ django support


##
# get a FeatureCollection out of a list of zone id
# Can be via GET or POST

# disable csrf protection 
@csrf_exempt
def json_zone_post(request):
    args = request.POST
    zones = args.getlist("ZID")
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
    zone_bbox = Polygon(((float(lowlat),float(lowlon)), (float(lowlat), float(highlon)), (float(highlat), float(highlon)), (float(highlat), float(lowlon)), (float(lowlat), float(lowlon))))
    spaces = AirSpaces.objects.filter(geom__bboverlaps=zone_bbox)
    js_spaces = geojson.FeatureCollection(list(spaces))

    return HttpResponse(geojson.dumps(js_spaces), mimetype='application/json')

def jsonID_zone_bbox(request, lowlat, lowlon, highlat, highlon):
    zone_bbox = Polygon(((float(lowlat),float(lowlon)), (float(lowlat), float(highlon)), (float(highlat), float(highlon)), (float(highlat), float(lowlon)), (float(lowlat), float(lowlon))))
    spaces = AirSpaces.objects.filter(geom__bboverlaps=zone_bbox)

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
