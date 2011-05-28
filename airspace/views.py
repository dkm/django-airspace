from django.http import HttpResponse
from airspace.models import AirSpaces
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.gis.geos import Polygon
import geojson

from django.http import Http404

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


def amap(request):
    all_as = AirSpaces.objects.all()
    return render_to_response('airspace/amap.html',
                              {'as_list' : all_as},
                              context_instance=RequestContext(request))
