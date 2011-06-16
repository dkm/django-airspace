# Create your models here.
# This is an auto-generated Django model module created by ogrinspect.
from django.contrib.gis.db import models
import geojson

class AirSpaces(models.Model):
    name = models.CharField(max_length=100)
    clazz = models.CharField(max_length=5)
    ceiling = models.CharField(max_length=200)
    floor = models.CharField(max_length=200)
    geom = models.PolygonField()
    objects = models.GeoManager()

    # So the model is pluralized correctly in the admin.
    class Meta:
        verbose_name_plural = "Air Spaces"

    @property
    def __geo_interface__(self):
        f = {'type': 'Feature',
             'id' : self.id,
             'properties': {'id':self.id,
                            'name': self.name,
                            'class': self.clazz,
                            'ceiling': geojson.loads(self.ceiling),
                            'floor': geojson.loads(self.floor)}, 
             'geometry': geojson.loads(self.geom.json)}

        return f
    
    # Returns the string representation of the model.
    def __unicode__(self):
        return self.name
