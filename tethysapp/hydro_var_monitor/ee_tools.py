import ee


#  IMERG 2000-06-01 -> 1 day lag, 30 min and monthly
# https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V06
imerg_30min_ic = ee.ImageCollection("NASA/GPM_L3/IMERG_V06")
# https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V06
imerg_1m_ic = ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V06")

# CHIRPS 1981-01-01 -> 1-2 months lag, Daily and Pentad
# https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY
chirps_daily_ic = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
# https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_PENTAD
chirps_pentad_ic = ee.ImageCollection('UCSB-CHG/CHIRPS/PENTAD')

# https://developers.google.com/earth-engine/datasets/catalog/NASA_USDA_HSL_SMAP10KM_soil_moisture
smap_ic = ee.ImageCollection('NASA_USDA/HSL/SMAP10KM_soil_moisture')

# https://developers.google.com/earth-engine/datasets/catalog/NOAA_GFS0P25
gfs_ic = ee.ImageCollection("NOAA/GFS0P25")

# https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_AN81d
prism_ic = ee.ImageCollection("OREGONSTATE/PRISM/AN81d")


def get_map_id(ic: ee.ImageCollection, vis_opts: dict = {}) -> str:
    """
    Get the map id for a given image collection.
    """
    return ic.getMapId(vis_opts)['tile_fetcher'].url_format
