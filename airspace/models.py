# Create your models here.
# This is an auto-generated Django model module created by ogrinspect.
from django.contrib.gis.db import models
import geojson

class AirSpaces(models.Model):
    name = models.CharField(max_length=100)
    clazz = models.CharField(max_length=5)

    start_date = models.DateTimeField()
    stop_date = models.DateTimeField()

    ext_info = models.CharField(max_length=200)

    ceil_alti = models.CharField(max_length=10)
    ceil_alti_m = models.FloatField()
    ceil_ref = models.CharField(max_length=4)
    ceil_f_sfc = models.BooleanField()
    ceil_unl = models.BooleanField()

    flr_alti = models.CharField(max_length=10)
    flr_alti_m = models.FloatField()
    flr_ref = models.CharField(max_length=4)
    flr_f_sfc = models.BooleanField()
    flr_unl = models.BooleanField()
    
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
                            'start_date' : self.start_date.strftime("%Y-%m-%d %H:%M"),
                            'stop_date' : self.stop_date.strftime("%Y-%m-%d %H:%M"),
                            'class': self.clazz,
                            'ceiling': {},
                            'floor': {}
                            }, 
             'geometry': geojson.loads(self.geom.json)}

        if self.ceil_alti.strip():
            f['properties']['ceiling']['alti'] = float(self.ceil_alti.split()[0])
            f['properties']['ceiling']['unit'] = self.ceil_alti.split()[1].strip()

        if self.ceil_ref.strip():
            f['properties']['ceiling']['ref'] = self.ceil_ref.strip()

        if self.ceil_f_sfc:
            f['properties']['ceiling']['asfc'] = True

        if self.ceil_unl:
            f['properties']['ceiling']['unl'] = True
        
        if self.flr_alti.strip():
            f['properties']['floor']['alti'] = float(self.flr_alti.split()[0])
            f['properties']['floor']['unit'] = self.flr_alti.split()[1].strip()

        if self.flr_ref.strip():
            f['properties']['floor']['ref'] = self.flr_ref.strip()

        if self.flr_f_sfc:
            f['properties']['floor']['asfc'] = True

        if self.flr_unl:
            f['properties']['floor']['unl'] = True
                
        return f
    
    # Returns the string representation of the model.
    def __unicode__(self):
        return self.name
