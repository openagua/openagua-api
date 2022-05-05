import io
from munch import Munch


def readfromzip(zf, subdir, path):
    try:
        bytes = io.BytesIO(zf.read(path))
    except:
        bytes = io.BytesIO(zf.read('/'.join([subdir, path])))
    return bytes


def shapefile2geojson(sfreader):
    fields = sfreader.fields[1:]
    field_names = [field[0] for field in fields]
    features = []
    for sr in sfreader.shapeRecords():
        properties = dict(zip(field_names, sr.record))
        geojson = {
            'type': 'Feature',
            'geometry': sr.shape.__geo_interface__,
            'properties': properties
        }
        features.append(Munch(geojson))
    return features


def get_resource_name(base_name, names):
    new_name = base_name
    i = 1
    while new_name in names:
        new_name = '{} ({})'.format(base_name, i)
        i += 1

    return new_name


def coords_to_string(coords, n=10):
    return str(round(coords[0], n)), str(round(coords[1], n))
