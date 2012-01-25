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
    ceil_fl = models.IntegerField(default=-1)
    ceil_ref = models.CharField(max_length=4)
    ceil_f_sfc = models.BooleanField()
    ceil_unl = models.BooleanField()

    flr_alti = models.CharField(max_length=10)
    flr_alti_m = models.FloatField()
    flr_fl = models.IntegerField(default=-1)
    flr_ref = models.CharField(max_length=4)
    flr_f_sfc = models.BooleanField()
    flr_unl = models.BooleanField()
    
    geom = models.PolygonField()
    objects = models.GeoManager()

    # So the model is pluralized correctly in the admin.
    class Meta:
        verbose_name_plural = "Air Spaces"

    def get_properties(self):
        f = {'id':self.id,
             'name': self.name,
             'start_date' : self.start_date.strftime("%Y-%m-%d %H:%M"),
             'stop_date' : self.stop_date.strftime("%Y-%m-%d %H:%M"),
             'class': self.clazz,
             'ext_info' : self.ext_info,
             'ceiling': {},
             'floor': {}
             }
        
        if self.ceil_alti.strip():
            f['ceiling']['alti'] = float(self.ceil_alti.split()[0])
            f['ceiling']['unit'] = self.ceil_alti.split()[1].strip()

        if self.ceil_ref.strip():
            f['ceiling']['ref'] = self.ceil_ref.strip()

        if self.ceil_fl != -1:
            f['ceiling']['flevel'] = self.ceil_fl

        if self.ceil_f_sfc:
            f['ceiling']['sfc'] = True

        if self.ceil_unl:
            f['ceiling']['unl'] = True
        
        if self.flr_alti.strip():
            f['floor']['alti'] = float(self.flr_alti.split()[0])
            f['floor']['unit'] = self.flr_alti.split()[1].strip()

        if self.flr_ref.strip():
            f['floor']['ref'] = self.flr_ref.strip()

        if self.flr_fl != -1:
            f['floor']['flevel'] = self.flr_fl
            
        if self.flr_f_sfc:
            f['floor']['sfc'] = True

        if self.flr_unl:
            f['floor']['unl'] = True

        return f
        
    @property
    def __geo_interface__(self):
        f = {'type': 'Feature',
             'id' : self.id,
             'properties': self.get_properties(), 
             'geometry': geojson.loads(self.geom.json)
             }
        return f
    
    # Returns the string representation of the model.
    def __unicode__(self):
        return '/'.join([self.name, str(self.start_date), str(self.stop_date), self.clazz, self.ceil_alti, str(self.ceil_alti_m), self.ceil_ref, str(self.ceil_f_sfc), str(self.ceil_unl), self.flr_alti, str(self.flr_alti_m), self.flr_ref, str(self.flr_f_sfc), str(self.flr_unl)])
