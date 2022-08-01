import ee


def create_ee(app):
    try:
        ee.Initialize()
        app.ee = ee

    except Exception as e:
        print(f'Earth Engine initialization error: {str(e)}')
        app.ee = None
