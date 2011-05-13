from django.contrib.gis import admin
from models import AirSpaces

admin.site.register(AirSpaces, admin.OSMGeoAdmin)
