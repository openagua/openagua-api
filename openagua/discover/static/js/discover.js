var networks;

var mapOptions = {
    contextmenu: true,
    condensedAttributionControl: false,
    zoomSnap: 0.5,
    zoomDelta: 0.5,
};

// CREATE BASIC MAP
var map, drawControl, miniMap;
var referenceLayers = {};

var tileOpts = {
    continuousWorld: false,
    nowrap: true,
    detectRetina: false,
};

$(function () {

    $(window).resize(function () {
        setMapHeight();
        map._onResize()
    });

    map = L.map('map', mapOptions);

// map events
    map.on('zoomend', function () {
        $('.leaflet-gac-control').val('');
    });

    $(document).on('click', '#menu-toggle', function () {
        setTimeout(map._onResize, 500);
    });

    tileOptions = {
        maxZoom: 18,
        //crossOrigin: true
    };

//tile layers

    var NoMap = L.tileLayer('', {attribution: ''});

    online = true;
    if (online) {

        var OpenAguaTiles = new L.tileLayer('https://api.mapbox.com/styles/v1/drheinheimer/cixc94qlw003r2qmu8z5nozor/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN,
            $.extend(tileOpts, {
                attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; OpenAgua.org'
            })
        );

        var greyscaleTiles = new L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            $.extend(tileOpts, {
                attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="http://cartodb.com/attributions">CartoDB</a>'
            })
        );

        var Esri_WorldTopoMap = new L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community [<a href="https://www.arcgis.com/home/item.html?id=30e5fe3149c34df1ba922e6f5bbf808f" target="_blank">More info</a>]',
            maxZoom: 17,
        });

//Google Maps
        if (useGoogle && validGoogleApiKey) {
            var googleAttribution = 'Map tiles &copy; Google. <a target="_blank" href="https://www.google.com/intl/en_us/help/terms_maps.html">Terms</a>';
            coreTiles = {
                'Google Road': googleMap('roadmap', googleAttribution),
                'Google Satellite': googleMap('satellite', googleAttribution),
                'Google Terrain': googleMap('terrain', googleAttribution),
                'Google Hybrid': googleMap('hybrid', googleAttribution),
            }
        } else {
            coreTiles = {
                'Mapbox Streets': new L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/streets-v9/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN, {
                    attribution: 'Map tiles &copy; <a target="_blank" href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a target="_blank" href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
                }),
                'Mapbox Satellite': new L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN, {
                    attribution: 'Map tiles &copy; <a target="_blank" href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a target="_blank" href="https://www.digitalglobe.com">DigitalGlobe</a>',
                }),
                'Mapbox Outdoors': new L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/outdoors-v9/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN, {
                    attribution: 'Map tiles &copy; <a target="_blank" href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a target="_blank" href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
                }),
                'Mapbox Satellite Streets': new L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v9/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN, {
                    attribution: 'Map tiles &copy; <a target="_blank" href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a target="_blank" href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> &copy; <a target="_blank" href="https://www.digitalglobe.com">DigitalGlobe</a>',
                }),
            }
        }

        var onlineMaps = $.extend(
            {
                "Esri World Topo": Esri_WorldTopoMap,
                "OpenAgua": OpenAguaTiles,
            },
            coreTiles,
            {
                "CartoDB Positron": greyscaleTiles,
            });
    } else {
        onlineMaps = {};
    }
    var baseMaps = $.extend(onlineMaps, {
        "[No base map]": NoMap
    });

    var layercontrol = new L.control.layers(baseMaps);

    Esri_WorldTopoMap.addTo(map); // add the tiles


// add zoom buttons
    var zoom = new L.control.zoom({position: 'topright'});

// add layer control
//     var overlayMaps = {
//         "Layers": activeItems
//     };

// scalebar
    var scale = new L.control.scale({
        position: 'bottomright',
    });

// minimap
//     var minimapTileLayer = new L.tileLayer(
//         'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {attribution: ''});

//Google Places autocomplete
    if (useGoogle && validGoogleApiKey) {
        var gplacesAutoComplete = new L.Control.GPlaceAutocomplete({
            position: 'topright',
            callback: function (place, map) {
                if (!place.geometry) {
                    failure("Location not found");
                    return;
                }
                if (place.geometry.viewport) {
                    var v = place.geometry.viewport;
                    var west = v.b.b, east = v.b.f, north = v.f.b, south = v.f.f;
                    var bounds = L.latLngBounds([south, west], [north, east]);
                    map.flyToBounds(bounds);
                } else {
                    map.flyTo([place.geometry.location.lat(), place.geometry.location.lng()], 17);
                }
            },
            prepend: false
        });
    }

    // miniMap = new L.Control.MiniMap(minimapTileLayer, {
    //     width: 175,
    //     height: 175,
    //     toggleDisplay: true,
    //     minimized: false,
    //     position: 'bottomleft',
    //     mapOptions: {condensedAttributionControl: false}
    // });

// ADD CONTROLS

//topleft

//topright
    if (useGoogle && validGoogleApiKey) {
        map.addControl(gplacesAutoComplete);
        $('.leaflet-gac-control')
            .attr('type', 'text')
            .attr('placeholder', 'Search map...')
            .wrap('<form class="gplaces-search-form"></form>');
        $('.gplaces-search-form')
            .append($('<button id="gplaces-clear">').addClass('close-icon close').attr('type', 'reset').html('&times;'));
        $('#gplaces-clear').on('click', function () {
            $('.leaflet-gac-control').val('');
        });
    }
    map.addControl(zoom);
    map.addControl(layercontrol);

//bottomright
    map.addControl(scale);

    //SHOW MAP

    setMapHeight();
    setDefaultView();

    // LOAD NETWORK & REFERENCES

    // NB: References on the web are loaded from Amazon S3. This can possibly be sped up by using EFS instead of S3.
    // loadNetworks(activeNetworkId, activeTemplateId);
});

function initializeItems(items) {
    items.eachLayer(function (layer) {
        var h, w, anchorx, anchory, nodeClass, linkClass, icon;
        var prop = layer.feature.properties;
        if (prop.name.indexOf('Junction') === -1 || layer.feature.geometry.type === 'LineString') {
            layer.bindTooltip(prop.name, {
                noHide: false,
            });
        }

        // update points
        if (layer.feature.geometry.type === 'Point') {

            if (prop.svg) {
                h = Number($(prop.svg).attr('height'));
                w = Number($(prop.svg).attr('height'));
                anchorx = Math.floor(w / 2);
                anchory = Math.ceil(h / 2);
                if (h === 11) {
                    anchory++
                }
                icon = new L.DivIcon({
                    iconSize: [w, h],
                    iconAnchor: [anchorx, anchory],
                    popupAnchor: [0, -15],
                    className: 'node',
                    html: prop.svg
                });
            } else {
                icon = new L.Icon({
                    // iconUrl: "/static/templates/" + prop.template_name + "/template/" + prop.image,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12],
                    popupAnchor: [0, -15],
                    className: 'node'
                });
            }
            layer.setIcon(icon); // add icon to map

            // update lines
        } else {

            layer.setStyle({
                color: prop.color,
                weight: prop.weight,
                dashArray: prop.dashArray,
                lineJoin: prop.lineJoin,
                opacity: prop.opacity,
                className: 'link'
            });
        }

    });
}
