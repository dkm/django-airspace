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

var geojsonloader = new OpenLayers.Format.GeoJSON({
    'internalProjection': new OpenLayers.Projection("EPSG:900913"),
    'externalProjection': new OpenLayers.Projection("EPSG:4326")
});

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
	$.getJSON('/airspace/json/' + to_get_s, 
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
