#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#   django-airspace
#   Copyright (C) 2010  Marc Poulhiès
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU Affero General Public License
#   as published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public
#   License along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

from django.http import HttpResponseRedirect, HttpResponseBadRequest
from airspace.models import AirSpaces
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.views.decorators.csrf import csrf_exempt

from django.middleware import csrf

from django.http import Http404

import os.path
import re
import osgeo.ogr

from airspace.helpers import loadFromGpx, get_space_intersect_path, save_upload, get_relief_profile_along_track, get_ceiling_floor_at_point, get_zone_profile_along_path, merge_touching_linestring, get_space_intersect_path


# this one can be used to get error when making an Ajax call...
# def json_track_upload(request):
#     try:
#         return json_track_upload__(request)
#     except:
#         import traceback
#         import sys
#         exc_info = sys.exc_info()
#         print "######################## Exception #############################"
#         print '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
#         print "################################################################"
    
## disable CSRF when debugging can help...
##@csrf_exempt
def json_track_upload( request ):
  if request.method == "POST":
    if request.is_ajax( ):
      # the file is stored raw in the request
      upload = request
      is_raw = True
      # AJAX Upload will pass the filename in the querystring if it is the "advanced" ajax upload
      try:
        filename = request.GET[ 'qqfile' ]
      except KeyError: 
        return HttpResponseBadRequest( "AJAX request not valid" )
    # not an ajax upload, so it was the "basic" iframe version with submission via form
    else:
      is_raw = False
      if len( request.FILES ) == 1:
        # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
        # ID based on a random number, so it cannot be guessed here in the code.
        # Rather than editing Ajax Upload to pass the ID in the querystring,
        # observer that each upload is a separate request,
        # so FILES should only have one entry.
        # Thus, we can just grab the first (and only) value in the dict.
        upload = request.FILES.values( )[ 0 ]
      else:
        raise Http404( "Bad Upload" )
      filename = upload.name

    dfilename = os.path.join("uploads", filename)
    
    # save the file
    success = save_upload( upload, dfilename, is_raw )

    return HttpResponseRedirect('/api/v1/intersections/gpx/' + filename + '/?format=json')


### Heavily based on code from http://kuhlit.blogspot.com/2011/04/ajax-file-uploads-and-csrf-in-django-13.html
### end of file-upload w/ django support
    
def amap(request):
    ctx = RequestContext( request, {
         'csrf_token': csrf.get_token( request ),
         } )
    
    all_as = AirSpaces.objects.all()
    return render_to_response('airspace/amap.html',
                              {'as_list' : all_as},
                              context_instance=ctx)
