from django.http import HttpResponse
from airspace.models import AirSpaces
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

from django.contrib.gis.geos import Polygon
import geojson

from django.http import Http404


##
# get a FeatureCollection out of a list of zone id
# Can be via GET or POST
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
    all_as = AirSpaces.objects.all()
    return render_to_response('airspace/amap.html',
                              {'as_list' : all_as},
                              context_instance=RequestContext(request))
