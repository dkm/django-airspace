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


var inter_colors = ["maroon", "red", "orange", "yellow", "olive",
		    "purple", "fuchsia", "white", "lime", "green",
		    "navy", "blue", "aqua", "teal", "black", "silver", 
		    "gray"];

var inter_colors_index = 0;

var inter_vectors;

/*
 * GeoJSON -> OL objs
 */
var geojsonloader = new OpenLayers.Format.GeoJSON({
    'internalProjection': new OpenLayers.Projection("EPSG:900913"),
    'externalProjection': new OpenLayers.Projection("EPSG:4326")
});

// Globals used to store data for GPX track
// (current marker, current track, track layer)
// used to store uploaded tracks
var track_layer;
var marker_feature;

var chart_timeout = null;
var chart_timeout_args = null;

// global GPX loader
var gpxloader = new OpenLayers.Format.GPX({
    'internalProjection': new OpenLayers.Projection("EPSG:900913"),
    'externalProjection': new OpenLayers.Projection("EPSG:4326")
});

var SHADOW_Z_INDEX = 10;
var MARKER_Z_INDEX = 11;

// change this for changing the style attached to the track
var track_style = {
    strokeColor: "orange", 
    strokeLinecap: 'round',
    strokeWidth: 2, 
    strokeOpacity: 1,
    graphicZIndex:0 // be sure this one is below the one used for other objects on the layer.
};

var inter_layer_style = new OpenLayers.StyleMap({
    strokeColor: "red",
    strokeWidth: 4,
    strokeLinecap: 'round',
    strokeOpacity: 1,
    graphicZIndex:1,
});

// this is the style attached to the track layer.
// This is also the style used for the marker.
var track_layer_style = new OpenLayers.StyleMap({
    // Set the external graphic and background graphic images.
    externalGraphic: 'http://' + document.location.host + static_root + "img/marker-gold.png",
    backgroundGraphic: 'http://' + document.location.host + static_root + "img/marker_shadow.png",

    // Makes sure the background graphic is placed correctly relative
    // to the external graphic.
    backgroundXOffset: 0,
    backgroundYOffset: -7,

    // Set the z-indexes of both graphics to make sure the background
    // graphics stay in the background (shadows on top of markers looks
    // odd; let's not do that).
    graphicZIndex: MARKER_Z_INDEX,
    backgroundGraphicZIndex: SHADOW_Z_INDEX,

    pointRadius: 10,
});

function initTrackLayer(){
    // layer for marker
    track_layer = new OpenLayers.Layer.Vector(
        "Track",
        {
	    projection: new OpenLayers.Projection("EPSG:4326"),
            styleMap: track_layer_style,
            //                    isBaseLayer: true,
            rendererOptions: {yOrdering: true,
			      zIndexing: true},
            renderers: renderer
        }
    );
    map.addLayer(track_layer);
}

function initIntersectionLayer() {
    inter_vectors = new OpenLayers.Layer.Vector(
	"INTERSECTION",
	{
	    styleMap: inter_layer_style,
	    renderers: renderer
	}
    );
    map.addLayer(inter_vectors);
}

function getTrackFromGpx(gpx_track_url, track_layer) {
    var gpx_track_data ;

    jQuery.ajax({
        url: gpx_track_url ,
        success: function(result) {
            gpx_track_data = result;                    
        },
        async:   false
    });

    var gpx_features = gpxloader.read(gpx_track_data);
    /*
     * the loader can return several features. Group them,
     * it will be easier to handle
     */
    var geom_collect = new OpenLayers.Geometry.Collection();
    var tmpArray = [];

    for (var i = 0; i < gpx_features.length; i++){
    	tmpArray.push(gpx_features[i].geometry);
    }
    geom_collect.addComponents(tmpArray);

    track_layer.addFeatures(new OpenLayers.Feature.Vector(geom_collect, {}, track_style));

    // join tracks
    var gpx_points = [];
    for (var i = 0; i < gpx_features.length; i++){
	var total = gpx_features[i].geometry.getVertices();
	for (var j = 0; j < total.length; j++) {
	    gpx_points.push(total[j]);
	}
    }

    return new OpenLayers.Geometry.LineString(gpx_points);
}

function trackDisplay(response, linestring_track) {
    if (track_layer == undefined) {
	initTrackLayer();
    }
    
    // purge any existing marker/track
    track_layer.removeAllFeatures();
    cleanIntersection();

    if (response.trackURL){
	var gpx_points = getTrackFromGpx(response.trackURL, track_layer);
    
	marker_feature = new OpenLayers.Feature.Vector(gpx_points[0]);
	track_layer.addFeatures([marker_feature]);
	handleChartTimed(gpx_points, response.relief_profile, response.intersections);
    } else if (linestring_track) {
	var ls_points = linestring_track.components;
	marker_feature = new OpenLayers.Feature.Vector(ls_points[0]);
	var track = new OpenLayers.Feature.Vector(linestring_track, {}, track_style);

	track_layer.addFeatures([marker_feature, track]);
	var ls_ol_points = [];
	for (var i=0; i < response.interpolated.coordinates.length; i++){
	    ls_ol_points.push(new OpenLayers.Geometry.Point(response.interpolated.coordinates[i][0], response.interpolated.coordinates[i][1]));
	}

	var ls_interpolated = new OpenLayers.Geometry.LineString(ls_ol_points);
	ls_interpolated.transform(map.displayProjection, map.projection);

	handleReliefChart(ls_interpolated, response.relief_profile, response.intersections, response.indexes);
    }
}

function refreshVerticalPlot(y_min, y_max, vertical_data) {
   var vertical_plot_options = {
	crosshair: { mode: "y" },
	yaxis: { 
	    min: y_min, 
	    max: y_max 
	},
	xaxis: {
	    min: 0,
	    max: 1
	}
    };

    var vert_plot = $.plot($("#chart-vertical"),
			   [],
			   vertical_plot_options
			  );
    if (vertical_data != undefined){
	vert_plot = $.plot($("#chart-vertical"),
			   vertical_data,
			   vertical_plot_options
			  );
    }
}


function relief_chart_hover() {
    if (chart_timeout_args.track_points.components.length > 0){
	if (marker_feature)
	    track_layer.destroyFeatures([marker_feature]);

	// we have to look for the nearest point
	var serie = chart_timeout_args.plot.getData()[0];
	var axes = chart_timeout_args.plot.getAxes();
	var xmin = axes.xaxis.datamin;
	var xmax = axes.xaxis.datamax;

	var pos_x = chart_timeout_args.pos.x > xmin ? chart_timeout_args.pos.x : xmin;
	if (pos_x > xmax) pos_x = xmax;

	var ratio = (pos_x-xmin)/(xmax-xmin);
	var i = Math.floor(ratio * (chart_timeout_args.track_points.components.length-1));
	
	if (serie.data[i][0] >= pos_x) {
	    for (; i > 0; i--) {
		if (serie.data[i][0]<pos_x)
		    break;
	    }
	} else {
	    for (; i < serie.data.length; i++) {
		if (serie.data[i][0]>pos_x)
		    break;
	    }
	}

	chart_timeout_args.plot.unhighlight();
	chart_timeout_args.plot.highlight(0,i);
	marker_feature = new OpenLayers.Feature.Vector(chart_timeout_args.track_points.components[i]);
	track_layer.addFeatures([marker_feature]);

	// handle vertical chart
	// var alti = chart_timeout_args.track_points[i].z;
	var ground = chart_timeout_args.relief_profile[i];

	var vertical_data = [];
	// vertical_data.push([[0,alti],[1,alti]]);
	vertical_data.push([[0,ground],[1,ground]]);

	// reset plot
	refreshVerticalPlot(chart_timeout_args.y_min, chart_timeout_args.y_max, vertical_data);
    }
    chart_timeout_args = null;
    chart_timeout = null;
}

function handleReliefChart(track_points, relief_profile, intersections, indexes) {
    var relief_points = [];
    var y_min = 0, y_max = 0;
    var idx_to_drop = [];

    var plot_data = [];

    for (var i = 0; i < relief_profile.length; i++){
	if (y_min > relief_profile[i]) {
	    y_min = relief_profile[i];
	} else if (y_max < relief_profile[i]) {
	    y_max = relief_profile[i];
	}
	relief_points.push([indexes[i], relief_profile[i]]);
    }
   
    var plot_options =            {
	selection: { mode: "x" },
	zoom: { interactive: true },
//        pan: { interactive: true },
        crosshair: { mode: "x" },
        grid: { hoverable: true,
                autoHighlight: false
              },
        yaxis: { 
	    min: y_min, 
	    max: y_max 
	},
    };

 
    // plot_data.push({
    //     data : track_points,
    //     lines: { show: true }
    // });
    plot_data.push({
	data : relief_points,
	lines: { show: true }
    });

    updateInterCount(intersections);
    for (var i=0; i < intersections.length; i++){
	mergeIndexInIntersection(intersections[i]);
	var ptop = {
	    data : intersections[i].data_top,
	    id : "int" + i,
	    lines : {show: true, fill: false}
	};

	var pbottom = {
	    data : intersections[i].data_bottom,
	    fillBetween: "int" + i,
	    lines : {show: true, fill: true}
	};

	plot_data.push(ptop);
	plot_data.push(pbottom);

	displayIntersection(intersections[i].inter);
    }

    var plot = $.plot($("#chart-placeholder"),
		      plot_data,
		      plot_options
		     );

    refreshVerticalPlot(y_min, y_max);

    $("#chart-placeholder").unbind("plothover");

    $("#chart-placeholder").bind("plothover",  function (event, pos, item) {
	if (!chart_timeout) {
	    chart_timeout_args = { track_points : track_points,
				   relief_profile : relief_profile,
				   plot : plot,
				   pos : pos,
				   event : event,
				   item : item,
				   y_min: y_min,
				   y_max : y_max};
	    chart_timeout = setTimeout(relief_chart_hover, 1);
	}

    });

    $("#chart-placeholder").unbind("plotselected");
    $("#chart-placeholder").bind("plotselected", function (event, ranges) {
        // do the zooming
        plot = $.plot($("#chart-placeholder"), plot_data,
                      $.extend(true, {}, plot_options, {
                          xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                      }));
    });
}

function mergeIndexInIntersection(intersection) {
    for (var i=0; i<intersection.data_top.length; i++){
        intersection.data_top[i] = [intersection.indexes[i], intersection.data_top[i]]
        intersection.data_bottom[i] = [intersection.indexes[i], intersection.data_bottom[i]]
    }
}

// function explodeIntersectionDataTopBottom(intersection, reference_path) {
//     for (var i=0; i<intersection.data_top.length; i++){
//         intersection.data_top[i] = [reference_path[intersection.start + i][0], intersection.data_top[i]]
//         intersection.data_bottom[i] = [reference_path[intersection.start + i][0], intersection.data_bottom[i]]
//     }
// }

/*
 * relief_profile: array with ground altitude indexed by gps points index (0 -> ...)
 * intersections: array of intersection object. Format still moving ;)
 */
function handleChartTimed(track_points, relief_profile, intersections) {
    var track_profile = [];
    var relief_points = [];

    var y_min = 0, y_max = 0;
    var prev_ts = 0;
    var idx_to_drop = [];

    var plot_data = [];

    for (var i = 0; i < track_points.components.length; i ++){
        var ele = track_points.components[i].z;
        if (ele < y_min) y_min = ele;
        else if (ele > y_max) y_max = ele;

	var ts = Date.parse(track_points.components[i].time).getTime();
	if (prev_ts < ts) {
            track_profile.push([ts, ele]);
            relief_points.push([ts, relief_profile[i]]);
	    prev_ts = ts;
	} else {
	    // deffer: drop track with timestamp not coherent with time
	    idx_to_drop.push(i);
	}
    }

    // drop track with timestamp not coherent with time
    // LOOKS BROKEN and triggers incoherency btw track_points and series.data
    // for (var i = 0; i<idx_to_drop.length; i++){
    // 	track_points.splice(idx_to_drop[i], idx_to_drop[i]);
    // }
    
    var plot_options =            {
	selection: { mode: "x" },
	zoom: { interactive: true },
//        pan: { interactive: true },
        crosshair: { mode: "x" },
        grid: { hoverable: true,
                autoHighlight: false
              },
        yaxis: { 
	    min: y_min, 
	    max: y_max 
	},
	xaxis : {
	    mode: "time",
	    timeformat: "%H:%M"
	}
    };

    plot_data.push({
        data : track_profile,
        lines: { show: true }
    });
    plot_data.push({
	data : relief_points,
	lines: { show: true }
    });

    // disabled, need resync with linear index + ts
    // updateInterCount(intersections);
    // for (var i=0; i < intersections.length; i++){
    // 	explodeIntersectionDataTopBottom(intersections[i], track_profile);

    // 	var ptop = {
    // 	    data : intersections[i].data_top,
    // 	    id : "int" + i,
    // 	    lines : {show: true, fill: false}
    // 	};

    // 	var pbottom = {
    // 	    data : intersections[i].data_bottom,
    // 	    fillBetween: "int" + i,
    // 	    lines : {show: true, fill: true}
    // 	};

    // 	plot_data.push(ptop);
    // 	plot_data.push(pbottom);
    // 	displayIntersection(intersections[i].inter);
    // }

    var plot = $.plot($("#chart-placeholder"),
		      plot_data,
		      plot_options
		     );
    refreshVerticalPlot(y_min, y_max);

    $("#chart-placeholder").unbind("plothover");
    $("#chart-placeholder").bind("plothover",  function (event, pos, item) {
        if (track_points.components.length > 0){
	    if (marker_feature)
		track_layer.destroyFeatures([marker_feature]);

	    // we have to look for the nearest point
	    var serie = plot.getData()[0];
	    var axes = plot.getAxes();
	    var xmin = axes.xaxis.datamin;
	    var xmax = axes.xaxis.datamax;

	    var pos_x = pos.x > xmin ? pos.x : xmin;
	    if (pos_x > xmax) pos_x = xmax;

	    var ratio = (pos_x-xmin)/(xmax-xmin);
	    var i = Math.floor(ratio * (track_points.components.length-1));
	    
	    if (serie.data[i][0] >= pos_x) {
		for (; i > 0; i--) {
		    if (serie.data[i][0]<pos_x)
			break;
		}
	    } else {
		for (; i < serie.data.length; i++) {
		    if (serie.data[i][0]>pos_x)
			break;
		}
	    }

	    plot.unhighlight();
	    plot.highlight(0,i);
	    marker_feature = new OpenLayers.Feature.Vector(track_points.components[i]);
	    track_layer.addFeatures([marker_feature]);

	    // handle vertical chart
	    var alti = track_points.components[i].z;
	    var ground = relief_profile[i];

	    var vertical_data = [];
	    vertical_data.push([[0,alti],[1,alti]]);
	    vertical_data.push([[0,ground],[1,ground]]);

	    // reset plot
	    refreshVerticalPlot(y_min, y_max, vertical_data);
        }

    });
    $("#chart-placeholder").unbind("plotselected");
    $("#chart-placeholder").bind("plotselected", function (event, ranges) {
        // do the zooming
        plot = $.plot($("#chart-placeholder"), plot_data,
                      $.extend(true, {}, plot_options, {
                          xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                      }));
    });


    // $("#chart-placeholder").bind("plotclick",  function (event, pos, item) {
    //     alert(pos.x + "/" + pos.y);
    // });
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

function cleanIntersection() {
    if (inter_vectors == undefined) {
	initIntersectionLayer();
    } else {
	inter_vectors.removeAllFeatures();
    }
}

function updateInterCount(intersections) {
    $('#inter_count').html('Intersections Count:' + intersections.length);
}

function displayIntersection(intersection) {
    if (inter_vectors == undefined) {
	initIntersectionLayer();
    }
    var features = geojsonloader.read(intersection);
    for (var i=0; i < features.length; i++){
    	features[i].style = {
    	    strokeColor: inter_colors[inter_colors_index],
    	    strokeWidth: 4,
    	    strokeLinecap: 'round',
    	    strokeOpacity: 1,
    	    graphicZIndex:1,
    	};
    	inter_colors_index = (inter_colors_index+1)%inter_colors.length;
    }
    inter_vectors.addFeatures(features);
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
    $('#zone_count').html("Zone Count:" + Object.keys(displayed).length);
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
