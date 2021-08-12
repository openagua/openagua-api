$(function () {

    var discoverTiles = new L.tileLayer(
        'https://api.mapbox.com/styles/v1/' + discoverMap + '/tiles/256/{z}/{x}/{y}?access_token=' + MAPBOX_ACCESS_TOKEN,
        $.extend(tileOpts, {
            attribution: '&copy; OpenAgua.org',
            zIndex: 100,
        })
    );
    discoverTiles.addTo(map);

});