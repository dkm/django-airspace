from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import os.path
import os
import tempfile

import json

from django.middleware import csrf

from django.http import Http404

from django import forms

from igc2kmz.igc import IGC
from igc2kmz import track
from igc2kmz.coord import Coord
from igc2kmz import Flight, flights2kmz

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

def upload(request):
    try:
        return upload_(request)
    except:
        import traceback
        import sys
        exc_info = sys.exc_info()
        print "######################## Exception #############################"
        print '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        print "################################################################"


## disable CSRF when debugging can help...
##@csrf_exempt
def upload_( request ):
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

        (tmp_id, tmp_up) = tempfile.mkstemp(suffix='-' + filename, dir="uploads")
        dfilename = tmp_up
        os.close(tmp_id)
    
        # save the file
        success = save_upload( upload, dfilename, is_raw )

        track = IGC(open(dfilename)).track()
        
        kmz = flights2kmz([Flight(track)],
                          roots=[],
                          tz_offset=0,
                          task=None)
        (tmp_id, tmp_up2) = tempfile.mkstemp(suffix='-' + filename + '.kmz', dir="uploads")
        os.close(tmp_id)
        kmz.write(tmp_up2, '2.2')
        os.unlink(tmp_up)

        ret_json = { 'success': success,
                     'track': tmp_up2.replace(os.path.join(os.getcwd(), 'uploads'),'/static/') }
        r = json.dumps( ret_json )

        return HttpResponse(r, mimetype='application/json' )


def index( request ):
    ctx = RequestContext( request, {
        'csrf_token': csrf.get_token( request ),
        } )
    return render_to_response('any2kmz/index.html',
                              {},
                              context_instance=ctx)

