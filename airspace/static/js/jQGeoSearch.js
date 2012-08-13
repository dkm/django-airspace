/***
|''Name''|jqGeoSearch|
|''Version''|0.3.51|
|''Source''|https://github.com/jdlrobson/jquery-plugins/raw/master/jQGeoSearch/jQGeoSearch.js|
!Usage
jQGeoSearch allows you to easily create client side pages that take a human readable place name and return you useful information like the longitude and latitude. To use simply use the following code to get started

{{{
	$(el).geoSearch({
		service: "nominatim", // other valid values are google, opengeocoding, openaddresses and nominatim
		handler: function(r) {
			console.log(r);
		},
		proxy: "/", // note the proxy takes a uri argument which is the lookup service
		proxyType: "post", // the method to use for the proxy server
		data: {} // additional data that should be posted to service (useful for adding additional parameters to proxy service)
	})
}}}
***/
//{{{
(function($) {

$.fn.extend({
	geoSearch: function(options) {
		options = ext.makeOptions(options);
		var container = this;
		var triggerSearch = function(val) {
			var resultsArea = $(".resultsArea", container)[0];
			$(resultsArea).text("Searching...");
			ext.lookupLngLat(val, resultsArea, options, options.handler || function() {});
		};
		var input = $("<input type='text' class='locationInput' name='location' size='14'/>").
			keypress(function(ev){
				if(ev.charCode === 13) {
					triggerSearch($(ev.target).val());
				}
			}).appendTo(container)[0];
		var results = $("<div />").addClass("resultsArea").appendTo(container)[0];
		$("<input type='button' class='find' value='center map'>").
			click(function(ev) {
				triggerSearch($(input).val());
				ev.preventDefault();
			}).appendTo(container);
		return this;
	}
});
var ext = $._geoSearch = {
	locale: {
		noresults: "Nothing found. To increase accuracy include country or postcode."
	},
	makeOptions: function(options) {
		if(!options) {
			options = {};
		}
		if(!options.proxy) {
			options.proxy = false;
		}
		if(!options.method) {
			options.method = "get";
		}
		if(!options.service) {
			options.service = "google";
		}
		if(!options.data) {
			options.data = {};
		}
		if(!options.dataType) {
			options.dataType = "json";
		}
		return options;
	},
	service: {
		google: {
			url: "http://google.co.uk/maps/api/geocode/json?sensor=true&address=%0&key=ABQIAAAAwEmbJkINlZVcIFvx5BkAbxSk4vLdUMb-MuG9rPFSkEREXU6fhxRLArDWPXvjwaxAfHeJFwN1Xncxeg",
			resultsPath: "results",
			lngLat: function(r) {
				return r.geometry.location;
			},
			humanReadable: function(r) {
				return r.formatted_address;
			}
		},
		opengeocoding: {
			url: "http://www.opengeocoding.org/geoservice_shrestha4_2.php?address=%0&address_id=&output=json",
			resultsPath: "Placemark",
			lngLat: function(r) {
				var p = r.Point.coordinates;
				return { lng: p[0], lat: p[1] };
			},
			humanReadable: function(r) {
				return r.address;
			}
		},
		openaddresses: {
			url: "http://www.openaddresses.org/search?query=%0",
			resultsPath: "features",
			lngLat: function(r) {
				var p = r.geometry.coordinates;
				return { lng: p[0], lat: p[1] };
			},
			humanReadable: function(r) {
				return r.properties.display;
			}
		},
		nominatim: {
			url: "http://open.mapquestapi.com/nominatim/v1/search.php?q=%0&format=json",
			resultsPath: false,
			lngLat: function(r) {
				return { lng: r.lon, lat: r.lat };
			},
			humanReadable: function(r) {
				return r.display_name;
			}
		}
	},
	init: function() {
		ext.service["default"] = ext.service.nominatim;
	},
	lookupLngLat: function(name, container, options, callback) {
		name = encodeURIComponent(name);
		var mode = ext.service[options.service] || ext.service["default"];
		var url = mode.url.replace("%0", name);
		var data = {}, lookupUrl;
		if(!options.proxy) {
			lookupUrl = url;
		} else {
			data.uri = url;
			lookupUrl = options.proxy;
		}
		data = $.extend(data, options.data);
		$.ajax({type: options.method, dataType: options.dataType, url: lookupUrl,
			data: data,
			contentType: "application/x-www-form-urlencoded", 
			success: function(geo) {
				$(container).empty();
				var i, result;
				var results = mode.resultsPath ? geo[mode.resultsPath] || [] : geo;
				if(results.length === 0) {
					$(container).text(ext.locale.noresults);
				} else if(results.length === 1 || (results.length > 0 && options.useTopResult)) {
					result = results[0];
					result.lngLat = mode.lngLat(result);
					result.humanReadable = mode.humanReadable(result);
					callback(result);
				} else {
					var clickHandler = function(ev) {
						ev.preventDefault();
						var target = ev.target;
						var data = $(target).data("geo.info");
						if(data) {
							callback(data);
						}
						$(container).empty();
					};
					for(i=0; i < results.length; i++) {
						result = results[i];
						result.lngLat = mode.lngLat(result);
						var formatted = mode.humanReadable(result);
						result.humanReadable = formatted;
						$("<a />").attr("href", "javascript:false;").
							text(formatted).data("geo.info", result).
							click(clickHandler).appendTo(container)[0];
					}
				}
			}
		});
	}
};
ext.init();

}(jQuery));
//}}}

