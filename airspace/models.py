# Create your models here.
# This is an auto-generated Django model module created by ogrinspect.
from django.contrib.gis.db import models

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

    # Returns the string representation of the model.
    def __unicode__(self):
        return self.name
