from django.conf.urls.defaults import patterns, include, url
from django.contrib.gis import admin

from django.views.generic import ListView

from airspace.models import AirSpaces

from tastypie.api import Api
from airspace.api import AirSpacesResource

v2_api = Api(api_name='v2')
v2_api.register(AirSpacesResource())

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'GDairspace.views.home', name='home'),
    # url(r'^GDairspace/', include('GDairspace.foo.urls')),
    url(r'^airspace/$', ListView.as_view(
        model=AirSpaces,
    )),

    url(r'^airspace/json/trackup$', 'airspace.views.json_track_upload'),

    url(r'^airspace/json/(?P<zone_id>\d+)$', 'airspace.views.json_zone'),
    url(r'^airspace/json/$', 'airspace.views.json_zone_post'),
    url(r'^airspace/json/name/(?P<name>.*)$', 'airspace.views.json_zones_by_name'),

    url(r'^airspace/json/path/id/$', 'airspace.views.json_path_id_post'),
                       
    url(r'^airspace/json/(?P<zone_ids>[\d,]+)$', 'airspace.views.json_zones'),

    url(r'^airspace/json/bbox/(?P<lowlat>-?[\d\.]+),(?P<lowlon>-?[\d\.]+),(?P<highlat>-?[\d\.]+),(?P<highlon>-?[\d\.]+)$', 'airspace.views.json_zone_bbox'),

    url(r'^airspace/json/point/id/(?P<lat>-?[\d\.]+),(?P<lon>-?[\d\.]+),(?P<radius>\d+)$', 'airspace.views.jsonID_zone_point'),

    url(r'^airspace/json/bbox/id/(?P<lowlat>-?[\d\.]+),(?P<lowlon>-?[\d\.]+),(?P<highlat>-?[\d\.]+),(?P<highlon>-?[\d\.]+)$', 'airspace.views.jsonID_zone_bbox'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^airspace/amap/', 'airspace.views.amap'),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    ## For django-piston
    (r'^api/', include('api.urls')),

    ## For django-tastypie
    (r'^api2/', include(v2_api.urls)),
)
