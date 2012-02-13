from django.conf.urls.defaults import patterns, include, url
from django.contrib.gis import admin

from django.views.generic import ListView

from airspace.models import AirSpaces

from tastypie.api import Api
from airspace.api import AirSpacesResource, AirSpacesIDResource, IntersectionsResource

v1_api = Api(api_name='v1')
v1_api.register(AirSpacesResource())
v1_api.register(AirSpacesIDResource())
v1_api.register(IntersectionsResource())

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

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^airspace/amap/', 'airspace.views.amap'),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    ## For django-tastypie
    (r'^api/', include(v1_api.urls)),
)
