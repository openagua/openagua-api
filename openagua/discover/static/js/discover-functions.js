function setMapHeight() {
    $('#map').height(getMapHeight());
}

function getMapHeight() {
    return $(window).outerHeight()
        - $('.navbar.navbar-fixed-top').outerHeight()
        - 1;
}

function setDefaultView() {
    map.setView([0, 0], 2);
}

// center the map on the selected point
function centerMap(e) {
    map.panTo(e.latlng);
}

// show the coordinates of the selected point
function showCoordinates(e) {
    var lat = e.latlng.lat;
    var lon = e.latlng.lng;
    if (e.relatedTarget !== undefined) {
        var gj = e.relatedTarget.toGeoJSON();
        if (gj.geometry.type === 'Point') {
            lon = gj.geometry.coordinates[0];
            lat = gj.geometry.coordinates[1];
        }
    }
    bootbox.alert("Latitude: " + lat.toFixed(3) + ", Longitude: " + lon.toFixed(3));
}

function googleMap(type, attribution) {
    return new L.gridLayer.googleMutant({type: type, attribution: attribution});
}