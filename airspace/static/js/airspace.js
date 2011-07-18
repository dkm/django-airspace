 // -*- coding: utf-8 -*-
 //   airspace checker
 //   Copyright (C) 2011  Marc Poulhiès

 //   This program is free software: you can redistribute it and/or modify
 //   it under the terms of the GNU General Public License as published by
 //   the Free Software Foundation, either version 3 of the License, or
 //   (at your option) any later version.

 //   This program is distributed in the hope that it will be useful,
 //   but WITHOUT ANY WARRANTY; without even the implied warranty of
 //   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 //   GNU General Public License for more details.

 //   You should have received a copy of the GNU General Public License
 //   along with this program.  If not, see <http://www.gnu.org/licenses/>.

var inter_vectors = new OpenLayers.Layer.Vector("INTERSECTION");


// Globals used to store data for GPX track
// (current marker, current track, track layer)
// used to store uploaded tracks
var gpx_track_layer;
var gpx_marker_layer;
var gpx_points = [];


/*
 *
 */

function trackDisplay(response){
    var trackURL = response.trackURL;

    // display the track in a separate layer that gets
    // reseted on every upload (should/could be changed...)
    if (gpx_track_layer) {
        map.removeLayer(gpx_track_layer);
    }
    if (gpx_marker_layer) {
        map.removeLayer(gpx_marker_layer);
    }

    var gpx_track_data ;

    jQuery.ajax({
        url: trackURL ,
        success: function(result) {
            gpx_track_data = result;                    
        },
        async:   false
    });          

    gpx_track_layer = new OpenLayers.Layer.Vector("GPX track:" + trackURL , {
	projection: new OpenLayers.Projection("EPSG:4326"),
        style: {strokeColor: "red", strokeWidth: 5, strokeOpacity: 0.5},
        renderers: renderer
    });
    var gpxloader = new OpenLayers.Format.GPX({
        'internalProjection': new OpenLayers.Projection("EPSG:900913"),
        'externalProjection': new OpenLayers.Projection("EPSG:4326")
    });
    var gpx_features = gpxloader.read(gpx_track_data);
    gpx_track_layer.addFeatures(gpx_features);
    map.addLayer(gpx_track_layer);
    center = gpx_features[0].geometry.getBounds().getCenterLonLat();
    map.panTo(center);


    var SHADOW_Z_INDEX = 10;
    var MARKER_Z_INDEX = 11;

    // layer for marker
    gpx_marker_layer = new OpenLayers.Layer.Vector(
        "Marker",
        {
            styleMap: new OpenLayers.StyleMap({
                // Set the external graphic and background graphic images.
                externalGraphic: static_root + "/img/marker-gold.png",
                backgroundGraphic: static_root + "/img/marker_shadow.png",
                
                // Makes sure the background graphic is placed correctly relative
                // to the external graphic.
                backgroundXOffset: 0,
                backgroundYOffset: -7,
                
                // Set the z-indexes of both graphics to make sure the background
                // graphics stay in the background (shadows on top of markers looks
                // odd; let's not do that).
                graphicZIndex: MARKER_Z_INDEX,
                backgroundGraphicZIndex: SHADOW_Z_INDEX,
                
                pointRadius: 10
            }),
            //                    isBaseLayer: true,
            rendererOptions: {yOrdering: true},
            renderers: renderer
        }
    );
    
    // join tracks
    gpx_points = [];
    for (var i = 0; i < gpx_features.length; i++){
	var total = gpx_features[i].geometry.getVertices();
	for (var j = 0; j < total.length; j++) {
	    gpx_points.push(total[j]);
	}
    }

    var marker_feature = [new OpenLayers.Feature.Vector(gpx_points[0])];
    gpx_marker_layer.addFeatures(marker_feature);
    map.addLayer(gpx_marker_layer);
    
    handleChart(response.relief_profile);
}


function handleChart(relief_profile) {
    var track_points = [];
    var relief_points = [];
    var y_min = 0, y_max = 0;

    for (var i = 0; i < gpx_points.length; i ++){
        var ele = gpx_points[i].z;
        if (ele < y_min) y_min = ele;
        else if (ele > y_max) y_max = ele;

        track_points.push([i, ele]);
        relief_points.push([i, relief_profile[i]]);
    }
    
    $.plot($("#chart-placeholder"),
           [{
               data : track_points,
               lines: { show: true }
           },
            {
                data : relief_points,
                lines: { show: true }
            }],
           {
               crosshair: { mode: "x" },
               grid: { hoverable: true,
                       autoHighlight: false,
                       clickable : true},
               yaxis: { min: y_min, max: y_max }
           }
          );

    $("#chart-placeholder").bind("plothover",  function (event, pos, item) {
        if (gpx_points.length > 0){
            gpx_marker_layer.destroyFeatures();
            gpx_marker_layer.addFeatures([new OpenLayers.Feature.Vector(gpx_points[Math.floor(pos.x) % gpx_points.length])]);
            $('#chart-legend').html("TOTO " + pos.x + "/" + pos.y + "||" + Math.floor(pos.x));
        }

    });

    $("#chart-placeholder").bind("plotclick",  function (event, pos, item) {
        alert(pos.x + "/" + pos.y);
    });
}

/*
 * Define style for displaying Airspaces.
 */

var renderer = OpenLayers.Util.getParameters(window.location.href).renderer;
renderer = (renderer) ? [renderer] : OpenLayers.Layer.Vector.prototype.renderers;
 
var styleMap = new OpenLayers.StyleMap({
    select : {
        fillColor: "#ff0000",
	fillOpacity: "0.7"
    }, 
});

var classStyleLookup = {
    "A"  : {fillColor: "#ee9900"},
    "CTR": {fillColor: "#f6072f"},
    "P"  : {fillColor: "#ff0000"},
    "Q"  : {fillColor: "#ee9900"},
    "E"  : {fillColor: "#00ff00"},
    "C"  : {fillColor: "#ee8800"},
    "D"  : {fillColor: "#ee7700"},
    "W"  : {fillColor: "#ee6600"},
    "R"  : {fillColor: "#ee5500"},
    "GP" : {fillColor: "#ee4400"},
};
styleMap.addUniqueValueRules("default", "class", classStyleLookup);


/*
 * How to load GeoJSON data for our map.
 */
var geojsonloader = new OpenLayers.Format.GeoJSON({
    'internalProjection': new OpenLayers.Projection("EPSG:900913"),
    'externalProjection': new OpenLayers.Projection("EPSG:4326")
});


/*
 * Below, we have only internal hacks :)
 */

var displayed = {};

function displayZoneInfo(feature) {
    var info = '<fieldset><legend>' +feature.attributes['name'] + '</legend>';
    info += '<ul>';
    info += '<li>Class: ' + feature.attributes['class'] + '</li>';
    info += '<li>Floor spec: ' + feature.attributes['ceiling'] + '</li>';
    info += '<li>Ceiling spec: ' + feature.attributes['floor'] + '</li>';
    info += '</li></fieldset>';
    $('#zone-info').html(info);
}

function clearZoneInfo(feature) {
    $('#zone-info').html("");
}

function displayIntersection(map, intersection) {
  var features = geojsonloader.read(intersection);
  inter_vectors.addFeatures(features);
  map.addLayers([inter_vectors]);
}

function displayAirspaces(vectors, aspace_gjson){
    var features = geojsonloader.read(aspace_gjson);
    vectors.addFeatures(features);
}

function getAndDisplay(vectors, space_list){

    var to_display = {};
    var already_displayed = {};
    var to_get = {};
    var to_get_s = undefined;

    $.each(space_list, function(idx) {
	var pk = space_list[idx];
	to_display[pk] = true;
	if (displayed[pk]){
	    already_displayed[pk] = true;
	} else {
	    to_get[pk] = true;
	    if (to_get_s == undefined)
		to_get_s = pk;
	    else
		to_get_s = to_get_s + "," + pk;
	}
    });

    $.each(displayed, function(k,p){
	if (!already_displayed[k]){
	    delete displayed[k];
	}
    });

    cleanDisplayed(vectors, to_display);

    if (to_get_s != undefined ){
	$.post('/airspace/json/', 
	       {
		   'ZID': to_get_s,
		   'csrfmiddlewaretoken' : global_csrf_token,
	       },
	       function(data) {
	           displayAirspaces(vectors, data);
		   $('#spinner-ajax-load').hide();
	       });
    } else {
	$('#spinner-ajax-load').hide();
    }

    displayed = to_display;
    $('#zone_count').html(Object.keys(displayed).length);
}

function cleanDisplayed(vectors, to_display) {
    var to_remove = [];
    $.each(vectors.features, function(idx){
	if (to_display[vectors.features[idx]['fid']] == undefined){
	    to_remove.push(vectors.features[idx]);
	}
    });
    vectors.destroyFeatures(to_remove);
}

function displayAirspace(map, aspaces){
            var report = function(e) {
	        if(e['feature']['attributes'].hasOwnProperty('name')){
	             $('#highlighted').html(e['feature']['attributes']['name']);
	        }
                OpenLayers.Console.log(e.type, e.feature.id);
            };
	    
            var selected = function(f) {
	       var str ="Name: " + f['attributes']['name'] + "<br/>";
	       str += "<ul>";
	       str += "<li>Floor:";
	      for (var i=0; i<f['attributes']['floor'].length; i++){
		  if (f['attributes']['floor'][i]['flevel']){
                       str+= "[ FL" + f['attributes']['floor'][i]['flevel'] + "]";
		  } else {
                      str+= "[" + f['attributes']['floor'][i]['ref'] +" " + f['attributes']['floor'][i]['basealti'] + "]";
                  }
              }

	      str += "</li>";
	       str += "<li>Ceil:";
	      for (var i=0; i<f['attributes']['ceiling'].length; i++){
                  if (f['attributes']['ceiling'][i]['flevel']){
		        str+= "[ FL" + f['attributes']['ceiling'][i]['flevel'] + "]";
	          } else {
                  	str+= "[" + f['attributes']['ceiling'][i]['ref'] + " " +f['attributes']['ceiling'][i]['basealti'] + "]";
		  }
              }

	      str += "</li>";
	       str += "<li>Class:" + f['attributes']['class'] + "</li>";
	       str += "</ul>";
	       $('#info').html(str);
            };

        var vectors_layers = new Array();								 
	for (var i=0; i<aspaces.length; i++) {
           var features = geojsonloader.read(aspaces[i]);
           var vectors = new OpenLayers.Layer.Vector(aspaces[i]['features'][0]['properties']['class']);
	   vectors.addFeatures(features);
           vectors_layers[i] = vectors;
        }
           map.addLayers(vectors_layers);

           var highlightCtrl = new OpenLayers.Control.SelectFeature(vectors_layers, {
                hover: true,
                highlightOnly: true,
                renderIntent: "temporary",
                eventListeners: {
                    beforefeaturehighlighted: report,
                    featurehighlighted: report,
                    featureunhighlighted: report
                }
           });

           var selectCtrl = new OpenLayers.Control.SelectFeature(vectors_layers,
                {clickout: true,
                 onSelect: selected
                }
           );
 
           map.addControl(highlightCtrl);
           map.addControl(selectCtrl);

           highlightCtrl.activate();
           selectCtrl.activate();

}
