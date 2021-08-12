$(function () {

    spinOn('Loading networks...')
    $.get(
        '/discover/get_study_geojson',
        {'id': study},
        function (resp) {
            gjLayer = new L.geoJson();
            map.addLayer(gjLayer);
            $.each(resp.features, function (i, feature) {
                gjLayer.addData(feature);
            });
            if (resp.features.length) {
                initializeItems(gjLayer);
                map.fitBounds(gjLayer.getBounds());
            } else {
                failure('Either the project is empty, or there are no public networks in the project.');
            }
            spinOff();
        }
    ).fail(
        function () {
            spinOff();
        }
    );
});
