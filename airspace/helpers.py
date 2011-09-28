import osgeo.ogr
from airspace.models import AirSpaces
import json
import ossim

from django.contrib.gis.geos import Point, LineString, MultiLineString

def loadFromGpx(gpxfilename, detectProjection=True):
    """
    From a GPX, loads all lines/multilines and returns a single
    geos representation (tracks are merged)
    """
    driver = osgeo.ogr.GetDriverByName('GPX')
    dataSource = driver.Open(gpxfilename, 0)

    # merge all track into a single track
    # this can be a problem, depending on why the there is multiple tracks...
    merged_points = []

    for i in xrange(dataSource.GetLayerCount()):
	layer = dataSource.GetLayer(i)
	layer.ResetReading()
	spatialRef = None
	if detectProjection:
            spatialRef = layer.GetSpatialRef()
	# elif useProj4:
	# 	spatialRef = osr.SpatialReference()
	# 	spatialRef.ImportFromProj4(sourceProj4)


	if spatialRef == None:	
            # No source proj specified yet? Then default to do no reprojection.
            # Some python magic: skip reprojection
            # altogether by using a dummy lamdba
            # funcion. Otherwise, the lambda will
            # be a call to the OGR reprojection
            # stuff.
            reproject = lambda(geometry): None
	else:
            destSpatialRef = osgeo.osr.SpatialReference()
            destSpatialRef.ImportFromEPSG(4326)	
            # Destionation projection will *always* be EPSG:4326,
            # WGS84 lat-lon
            coordTrans = osgeo.osr.CoordinateTransformation(spatialRef,destSpatialRef)
            reproject = lambda(geometry): geometry.Transform(coordTrans)
        featureDefinition = layer.GetLayerDefn()


	for j in range(layer.GetFeatureCount()):
            feature = layer.GetNextFeature()
            geometry = feature.GetGeometryRef()
            geometryType = geometry.GetGeometryType()

            ls = []

            if  geometryType == osgeo.ogr.wkbLineString or geometryType == osgeo.ogr.wkbLineString25D:
                if geometry.GetPointCount() <= 2:
                    continue
                ls.append(geometry)
            elif geometryType == osgeo.ogr.wkbMultiLineString or geometryType == osgeo.ogr.wkbMultiLineString25D:
                for i in xrange(geometry.GetGeometryCount()):
                    subgeom = geometry.GetGeometryRef(i)
                    if subgeom.GetPointCount() <= 2:
                        continue
                    else:
                        ls.append(subgeom)

            for line in ls:
                reproject(line)
                for i in xrange(line.GetPointCount()):
                    merged_points.append(line.GetPoint(i))

    merged_line = LineString(merged_points)
    return merged_line


### from file-upload w/ django support
### Heavily based on code from http://kuhlit.blogspot.com/2011/04/ajax-file-uploads-and-csrf-in-django-13.html
def save_upload( uploaded, filename, raw_data ):
    ''' 
    raw_data: if True, uploaded is an HttpRequest object with the file being
        the raw post data 
        if False, uploaded has been submitted via the basic form
        submission and is a regular Django UploadedFile in request.FILES
    '''
    try:
        from io import FileIO, BufferedWriter
        with BufferedWriter( FileIO( filename, "wb" ) ) as dest:
            # if the "advanced" upload, read directly from the HTTP request 
            # with the Django 1.3 functionality
            if raw_data:
                foo = uploaded.read( 1024 )
                while foo:
                    dest.write( foo )
                    foo = uploaded.read( 1024 ) 
            # if not raw, it was a form upload so read in the normal Django chunks fashion
            else:
                for c in uploaded.chunks( ):
                    dest.write( c )
            # got through saving the upload, report success
            return True
    except IOError:
        # could not open the file most likely
        pass
    return False



def get_relief_profile_along_track(track):
    """
    track should be a list of coord.
    """
    ossim.init('XXX/ossim_preferences_template')

    relief_profile = []
    # pnt = GEOSGeometry(track)
    for p in track:
        h = ossim.height(p[1], p[0])
            ## if data not available, default to 0
        if h:
            relief_profile.append(h[1])
        else:
            relief_profile.append(0)
    
    return relief_profile

def get_ceiling_floor_at_point(airspace, point):
    ceil,floor = None, None

    if airspace.ceil_fl != -1:
        ceil =  airspace.ceil_fl * 100 * 0.3048
    elif airspace.ceil_ref and airspace.ceil_ref == 'AGL':
        try:
            h = ossim.height(point[1], point[0])
            ceil = airspace.ceil_alti_m + h[1]
        except:
            ## most probably: no ground info :(
            ceil = 0
    elif airspace.ceil_ref and airspace.ceil_ref == 'AMSL':
        ceil = airspace.ceil_alti_m
    elif airspace.ceil_unl:
        ceil = 100000


    if airspace.flr_fl != -1:
        flr =  airspace.flr_fl * 100 * 0.3048
    elif airspace.flr_ref and airspace.flr_ref == 'AGL':
        try:
            h = ossim.height(point[1], point[0])
            flr = airspace.flr_alti_m + h[1]
        except:
            ## most probably: no ground info :(
            flr = 0
    elif airspace.flr_ref and airspace.flr_ref == 'AMSL':
        flr = airspace.flr_alti_m
    elif airspace.flr_f_sfc:
        try:
            h = ossim.height(point[1], point[0])
            floor = h[1]
        except:
            ## most probably: no gound info :'(
            floor = 0
    
    return (ceil,floor)

def get_zone_profile_along_path(airspace, path):
    floor = []
    ceiling = []
    minh, maxh = 100000,-1

    for point in path:
        c,f = get_ceiling_floor_at_point(airspace, point)
        floor.append(f)
        ceiling.append(c)
        if f < minh:
            minh = f
            
        if c > maxh:
            maxh = c
    return (floor, ceiling, minh, maxh)


def merge(ML):
    if len(ML) == 1:
        return ML[0]

    coords = list(ML[0])
    for ls in ML[1:-1]:
        coords += list(ls)[1:-1]
    coords += list(ML[-1][1:])
    return LineString(coords)

def merge_touching_linestring(multiLS):
    buf = [multiLS[0]]
    final = []
    
    for i,ls in enumerate(multiLS[1:]):
        prev_p = buf[-1][-1]
        next_p = ls[0]
        if prev_p[0] == next_p[0] and prev_p[1] == next_p[1]:
            buf.append(ls)
        else:
            ml = MultiLineString(buf)
            final.append(merge(ml))
            buf = [ls]
    if len(buf) > 2:
        ml = MultiLineString(buf)

        final.append(merge(ml))
    else:
        final.append(buf[0])
    return final
    

def get_space_intersect_path(path, height_limit=None):
    spaces = AirSpaces.objects.filter(geom__intersects=path)

    data = {} ##serializers.serialize('json', spaces, fields=[])
    inters = []

    for iz in spaces:
        intersect = path.intersection(iz.geom)
       
        if intersect.geom_typeid == 1: ## LineString
            nls = intersect
            
            floor, ceiling, minh, maxh = get_zone_profile_along_path(iz, nls)
            if not height_limit or minh < height_limit:
                data[iz.pk] = True
                inters.append({
                        'zid' : iz.pk,
                        'inter': json.loads(nls.json),
                        'minh' : minh,
                        'maxh' : maxh,
                        'data_top' : floor,
                        'data_bottom': ceiling,
                        'indexes' : [path.project(Point(x)) for x in nls],
                        })
        elif intersect.geom_typeid == 5: ## MultiLineString
            intersect_merged =  merge_touching_linestring(intersect)

            for ls in intersect_merged:
                nls = ls
                floor, ceiling, minh, maxh = get_zone_profile_along_path(iz, nls)
                if not height_limit or minh < height_limit:
                    data[iz.pk] = True
                    inters.append({
                            'zid' : iz.pk,
                            'inter': json.loads(nls.json),
                            'data_top' : floor,
                            'data_bottom': ceiling,
                            'minh' : minh,
                            'maxh' : maxh,
                            'indexes' : [path.project(Point(x)) for x in nls],
                            })
        
    return (data.keys(), inters)
