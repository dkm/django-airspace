from django.conf.urls.defaults import patterns, include, url
from django.contrib.gis import admin

from django.views.generic import ListView

from airspace.models import AirSpaces

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
    url(r'^airspace/json/(?P<zone_id>\d+)$', 'airspace.views.json_zone'),
    url(r'^airspace/json/bbox/(?P<lowlat>-?[\d\.]+),(?P<lowlon>-?[\d\.]+),(?P<highlat>-?[\d\.]+),(?P<highlon>-?[\d\.]+)$', 'airspace.views.json_zone_bbox'),
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^airspace/amap/', 'airspace.views.amap'),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
