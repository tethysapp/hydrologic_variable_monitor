import ee

'''def get_map_id(ic: ee.ImageCollection, vis_opts: dict = {}) -> str:
    """
    Get the map id for a given image collection.
    """
    return ic.getMapId(vis_opts)['tile_fetcher'].url_format'''


def ERA5(band):
    ic = ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY").filterDate('1983-01-01', '2023-01-01').select(band).reduce(
        ee.Reducer.mean())
    return ic


def GLDAS(band):
    ic = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").filterDate('2022-01-01', '2023-01-01').select(band).reduce(
        ee.Reducer.mean())
    return ic


def IMERG(band):
    ic = ee.ImageCollection("NASA/GPM_L3/IMERG_V06").filterDate('2022-07-01', '2023-01-01').select(band).reduce(
        ee.Reducer.mean())
    return ic


def CHIRPS(band):
    ic = ee.ImageCollection("UCSB-CHG/CHIRPS/PENTAD").filterDate('2022-01-01', '2023-01-01').select(band).reduce(
        ee.Reducer.mean())
    return ic


def get_tile_url(ee_image, vis_params):
    map_id_dict = ee.Image(ee_image).getMapId(vis_params)
    return map_id_dict['tile_fetcher'].url_format


def NDVI(region):
    # Define a point of interest. Use the UI Drawing Tools to import a point
    # geometry and name it "point" or set the point coordinates with the
    # ee.Geometry.Point() function as demonstrated here.
    get_coord = region["geometry"]
    area= ee.Geometry.Polygon(get_coord["coordinates"])
    #print(point)

    # Import the Landsat 8 TOA image collection.
    l8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA');

    # Get the least cloudy image in 2015.
    image = ee.Image(
        l8.filterBounds(area)
        .filterDate('2021-01-01', '2022-12-31')
        .sort('CLOUD_COVER')
        .first()
    );

    # Compute the Normalized Difference Vegetation Index (NDVI).
    nir = image.select('B5');
    red = image.select('B4');
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI');

    return ndvi
