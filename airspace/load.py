import os
from django.contrib.gis.utils import LayerMapping
from models import AirSpaces

airspaces_mapping = {
    'name' : 'NAME',
    'clazz' : 'CLASS',
    'ceiling' : 'CEILING',
    'floor' : 'FLOOR',
    'geom' : 'POLYGON',
}

airspace_shp = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/layer.shp'))

def run(verbose=True):
    lm = LayerMapping(AirSpaces, airspace_shp, airspaces_mapping,
                      transform=False, encoding='UTF-8')

    lm.save(strict=True, verbose=verbose)
