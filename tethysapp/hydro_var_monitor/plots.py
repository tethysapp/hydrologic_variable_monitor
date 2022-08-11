from datetime import date
import datetime
import ee
import pandas as pd
import numpy as np
import calendar


# define functions
def get_current_date():
    now = date.today().strftime("%Y-%m-%d")
    avg_start = date.today().replace(year=date.today().year - 30).strftime("%Y-%m-%d")
    y2d_start = date(date.today().year, 1, 1).strftime("%Y-%m-%d")
    return now, avg_start, y2d_start


def get_collection(collection_name, xy_point, start_date='1992-01-01', end_date='2023-01-01'):
    return (
        ee.ImageCollection(collection_name)
        .filterBounds(xy_point)
        .filterDate(start_date, end_date)
    )


def set_ymd_properties(img):
    date = ee.Date(img.get('system:time_start'))
    return img.set({
        'date': date.format('YYYY-MM-DD'),
        'month_day': date.format('MM-DD'),
        'year': date.format('YYYY'),
        'month': date.format('MM'),
        'day': date.format('DD')
    })


def plot_ERA5(region, band, title, yaxis):
    now, avg_start, y2d_start = get_current_date()

    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])
    # read in img col
    img_col_avg = ee.ImageCollection(
        [f'users/rachelshaylahuber55/era5_monthly_avg/era5_monthly_{i:02}' for i in range(1, 13)])
    img_col_y2d = get_collection("ECMWF/ERA5_LAND/HOURLY", point, y2d_start, now)

    # define functions that will be applied
    def get_val_at_xypoint(img):
        # reduction function
        temp = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            maxPixels=1e12,
        )
        # set the result as a metadata property in the image
        return img.set(temp)

    def get_df(band_name, img_col, region):
        era_df = img_col.select(band_name)
        era_with_property = era_df.map(get_val_at_xypoint)
        # create an array of values that are extracted from image collection
        array_of_values = era_with_property.aggregate_array(band_name).getInfo()
        array_of_datetime_values = era_with_property.aggregate_array('system:time_start').getInfo()
        # find the average by day
        datetime = pd.to_datetime(np.array(array_of_datetime_values) * 1e6)
        df = pd.DataFrame(array_of_values, index=datetime)
        df['day'] = pd.to_datetime(df.index)
        df['day'] = df['day'].dt.strftime('%m-%d')
        return df.groupby('day').mean()

    def avg_era(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=1e6,
        ))

    avg_img = img_col_avg.select(band).map(avg_era)
    y2d_df = get_df(band, img_col_y2d, point)

    avg_df = pd.DataFrame(
        avg_img.aggregate_array('avg_value').getInfo(),
        # index=np.array(gldas_avg.aggregate_array('month').getInfo()).astype(int),
    )
    # set date and data values columns that the js code will look for
    avg_df.columns = ["data_values"]
    avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=avg_df.index[i] + 1, day=15) for i in avg_df.index]
    avg_df['date'] = avg_df['datetime'].dt.strftime("%Y-%m-%d")
    avg_df.reset_index(drop=True, inplace=True)
    # set year to date values
    y2d_df.columns = ["data_values"]
    y2d_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=int(i[:2]), day=int(i[3:5])) for i in y2d_df.index]
    y2d_df['date'] = y2d_df['datetime'].dt.strftime("%Y-%m-%d")
    y2d_df.reset_index(drop=True, inplace=True)
    # precipitation must be cumulatively summer throughout the year
    if band == "total_precipitation":
        date_generated = pd.date_range(y2d_start, periods=365)
        cum_df = pd.DataFrame(date_generated)
        values_list = []
        for date in cum_df[0]:
            i = 1
            for val in avg_df["data_values"]:
                if date.month == i:
                    values_list.append(val)
                i = i + 1
        # multiply by 1000 to convert into mm from meters
        cum_df['val_per_day'] = values_list
        cum_df['date'] = cum_df[0].dt.strftime("%Y-%m-%d")
        cum_df["data_values"] = (cum_df['val_per_day'] * 1000).cumsum()
        avg_df = cum_df

    if band == "total_precipitation":
        y2d_df["data_values"] = (y2d_df["data_values"] * 1000).cumsum()
    else:
        y2d_df["data_values"] = y2d_df["data_values"]

    Dict = {'avg': avg_df, 'y2d': y2d_df, 'title': title, 'yaxis': yaxis}

    return Dict


def plot_GLDAS(region, band, title, yaxis):
    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])
    gldas_ic = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")

    # define necessary functions
    def clip_to_bounds(img):
        return img.updateMask(ee.Image.constant(1).clip(point).mask())

    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=1e6,
        ))

    # read in assets from the gldas_monthly folder
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)
    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
    )
    # precipitation must be summed
    if band == "Rainf_tavg":
        date_generated = pd.date_range(y2d_start, periods=365)
        cum_df = pd.DataFrame(date_generated)
        values_list = []
        for date in cum_df[0]:
            i = 1
            for val in gldas_avg_df["Rainf_tavg"]:
                if date.month == i:
                    # convert from seconds to days
                    values_list.append(val * 86400)
                i = i + 1
        cum_df['val_per_day'] = values_list
        cum_df['date'] = cum_df[0].dt.strftime("%Y-%m-%d")
        cum_df["data_values"] = cum_df['val_per_day'].cumsum()
        gldas_avg_df = cum_df
    else:
        gldas_avg_df["data_values"] = gldas_avg_df[band]
        gldas_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=gldas_avg_df.index[i] + 1, day=15)
                                    for i in gldas_avg_df.index]
        gldas_avg_df['date'] = gldas_avg_df['datetime'].dt.strftime("%Y-%m-%d")

    gldas_ytd = gldas_ic.select(band).filterDate(y2d_start, now).map(clip_to_bounds).map(avg_gldas)
    gldas_ytd_df = pd.DataFrame(
        gldas_ytd.aggregate_array('avg_value').getInfo(),
        index=pd.to_datetime(np.array(gldas_ytd.aggregate_array('system:time_start').getInfo()) * 1e6)
    )
    gldas_ytd_df['date'] = gldas_ytd_df.index.strftime("%Y-%m-%d")

    if band == "Rainf_f_tavg":
        gldas_ytd_df["data_values"] = (gldas_ytd_df[band] * 10800).cumsum()
    else:
        gldas_ytd_df["data_values"] = gldas_ytd_df[band]
        gldas_ytd_df = gldas_ytd_df.groupby('date').mean()
        gldas_ytd_df.rename(index={0: 'index'}, inplace=True)
        gldas_ytd_df['date'] = gldas_ytd_df.index

    Dict = {'avg': gldas_avg_df, 'y2d': gldas_ytd_df, 'title': title, 'yaxis': yaxis}
    print(Dict)

    return Dict


def plot_IMERG(region):
    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])

    def avg_in_bounds(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
        ))

    imerg_1m_ic = ee.ImageCollection(
        [f'users/rachelshaylahuber55/imerg_monthly_avg/imerg_monthly_avg_{i:02}' for i in range(1, 13)])

    imerg_1m_values_ic = imerg_1m_ic.select('HQprecipitation').map(avg_in_bounds)

    imerg_1m_df = pd.DataFrame(
        imerg_1m_values_ic.aggregate_array('avg_value').getInfo(),
    ).dropna()

    print(imerg_1m_df)

    date_generated = pd.date_range(y2d_start, periods=365)
    cum_df = pd.DataFrame(date_generated)

    values_list = []
    for date in cum_df[0]:
        i = 1
        # print("printing date")
        # print (date)
        for val in imerg_1m_df["HQprecipitation"]:
            if date.month == i:
                values_list.append(val * 24)
            i = i + 1
    # print(values_list)

    cum_df["val_per_day"] = values_list
    cum_df["data_values"] = cum_df["val_per_day"].cumsum()

    cum_df['date'] = cum_df[0].dt.strftime("%Y-%m-%d")
    print(cum_df)

    imerg_30min_ic = ee.ImageCollection("NASA/GPM_L3/IMERG_V06")

    imerg_ytd_values_ic = imerg_30min_ic.select('HQprecipitation').filterDate(y2d_start, now).map(avg_in_bounds)

    imerg_ytd_df = pd.DataFrame(
        imerg_ytd_values_ic.aggregate_array('avg_value').getInfo(),
        index=pd.to_datetime(np.array(imerg_ytd_values_ic.aggregate_array('system:time_start').getInfo()) * 1e6),
    )

    # group half hourly values by day of the year
    imerg_ytd_df = imerg_ytd_df.groupby(imerg_ytd_df.index.strftime('%j')).mean()
    # convert day-of-year to datetime, add 1 to day so it is plotted at end of day it represents
    imerg_ytd_df.index = [datetime.datetime.strptime(f'{int(now[:4])}-{int(i) + 1}', "%Y-%j") for i in
                          imerg_ytd_df.index]
    # cumulative depth = average mm/hr per day * 24 hours/day
    imerg_ytd_df['data_values'] = imerg_ytd_df['HQprecipitation'].cumsum() * 24
    imerg_ytd_df['date'] = imerg_ytd_df.index.strftime("%Y-%m-%d")

    yaxis = "mm of precipitación"
    title = "Acumulados de Precipitación - IMERG"

    Dict = {'avg': cum_df, 'y2d': imerg_ytd_df, 'yaxis': yaxis, 'title': title}

    return Dict


def plot_CHIRPS(region):
    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])
    chirps_daily_ic = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
    chirps_pentad_ic = ee.ImageCollection(
        [f'users/rachelshaylahuber55/chirps_monthly_avg/chirps_monthly_avg_{i:02}' for i in range(1, 13)])

    def clip_to_bounds(img):
        return img.updateMask(ee.Image.constant(1).clip(point).mask())

    def chirps_avg(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
        ).get('precipitation'))

    days_in_month = np.array([calendar.monthrange(int(now[:4]), i)[1] for i in range(1, 13)])

    chirps_avg_ic = chirps_pentad_ic.select('precipitation').map(clip_to_bounds).map(
        chirps_avg)
    chirps_df = pd.DataFrame(
        chirps_avg_ic.aggregate_array('avg_value').getInfo(),

        columns=['depth', ]
    ).dropna()
    # chirps_monthly_df = chirps_df.groupby(chirps_df.index.strftime('%m')).mean()
    # chirps_monthly_df.index = chirps_monthly_df.index.astype(int)

    chirps_df['data_values'] = chirps_df['depth'].cumsum() * days_in_month / 5
    chirps_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=chirps_df.index[i] + 1, day=15) for i in
                             chirps_df.index]
    # chirps_df = pd.concat(
    # [pd.DataFrame([[0, 0, datetime.datetime(int(now[:4]), 1, 1)], ], columns=chirps_df.columns),
    # chirps_df])
    chirps_df['date'] = chirps_df['datetime'].dt.strftime("%Y-%m-%d")

    chirps_ytd_ic = chirps_daily_ic.filterDate(y2d_start, now).select('precipitation').map(clip_to_bounds).map(
        chirps_avg)

    chirps_ytd_df = pd.DataFrame(
        chirps_ytd_ic.aggregate_array('avg_value').getInfo(),
        index=pd.to_datetime(np.array(chirps_ytd_ic.aggregate_array('system:time_start').getInfo()) * 1e6),
        columns=['depth', ]
    )
    chirps_ytd_df.index.name = 'datetime'
    chirps_ytd_df['data_values'] = chirps_ytd_df['depth'].cumsum()
    chirps_ytd_df['date'] = chirps_ytd_df.index.strftime("%Y-%m-%d")
    yaxis = "mm of precipitación"
    title = "Acumulados de Precipitación - CHIRPS"

    Dict = {'avg': chirps_df, 'y2d': chirps_ytd_df, 'yaxis': yaxis, 'title': title}

    return Dict


def plot_NDVI(region):
    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])

    # functions needed to get data
    # adds ndvi as a band
    def add_ndvi(img):
        return img.addBands(img.normalizedDifference(['nir', 'red']).rename('ndvi'))

    # controls for clouds
    def qa_mask(image):
        # Bits 3, 4, and 5 are cloud shadow, snow, and cloud, respectively.
        cloudShadowBitMask = (1 << 3);
        cloudsBitMask = (1 << 5);
        snowBitMask = (1 << 4);

        # Get the pixel QA band.
        qa = image.select('pixel_qa');

        # apply the bit shift and get binary image of different QA flags
        cloud_shadow_qa = qa.bitwiseAnd(cloudShadowBitMask).eq(0)
        snow_qa = qa.bitwiseAnd(snowBitMask).eq(0)
        cloud_qa = qa.bitwiseAnd(cloudsBitMask).eq(0)

        # combine qa mask layers to one final mask
        mask = cloud_shadow_qa.And(snow_qa).And(cloud_qa)

        # apply mask and return orignal image
        return image.updateMask(mask);
    def qa_mask_L8(image):
        # Bits 3, 4, and 5 are cloud shadow, snow, and cloud, respectively.
        cloudShadowBitMask = (1 << 3);
        cloudsBitMask = (1 << 5);
        snowBitMask = (1 << 4);

        # Get the pixel QA band.
        qa = image.select('QA_PIXEL');

        # apply the bit shift and get binary image of different QA flags
        cloud_shadow_qa = qa.bitwiseAnd(cloudShadowBitMask).eq(0)
        snow_qa = qa.bitwiseAnd(snowBitMask).eq(0)
        cloud_qa = qa.bitwiseAnd(cloudsBitMask).eq(0)

        # combine qa mask layers to one final mask
        mask = cloud_shadow_qa.And(snow_qa).And(cloud_qa)

        # apply mask and return orignal image
        return image.updateMask(mask);

    def landsat_avg(img):
        return img.set('avgndvi', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=150,
            maxPixels=1e12,
        ).get('ndvi'))

    # load on Landsat 5 collection
    l5_collection = (
        ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
        # filter by sample locations
        .filterBounds(point)
        # apply qa mask
        .map(qa_mask)
        # select the spectral bands and rename
        .select(
            ["B1", "B2", "B3", "B4", "B5", "B7"],
            ["blue", "green", "red", "nir", "swir1", "swir2"]
        )
    )
    # load on Landsat 7 collection
    l7_collection = (
        ee.ImageCollection('LANDSAT/LE07/C01/T1_SR')
        # filter by sample locations
        .filterBounds(point)
        # apply qa mask
        .map(qa_mask)
        # select the spectral bands and rename
        .select(
            ["B1", "B2", "B3", "B4", "B5", "B7"],
            ["blue", "green", "red", "nir", "swir1", "swir2"]
        )
    )
    # load on Landsat 8 collection
    l8_collection = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        # filter by sample locations
        .filterBounds(point)
        # apply qa mask
        #.map(qa_mask_L8)
        # select the spectral bands and rename
        .select(
            ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"],
            ["blue", "green", "red", "nir", "swir1", "swir2"]
        )
    )

    # merge all of the collections together for long time series
    landsat_ic = l5_collection.merge(l7_collection).merge(l8_collection).filterBounds(point).map(add_ndvi).select(
        'ndvi').filterDate(avg_start, now).map(landsat_avg).map(set_ymd_properties)
    month_list = ee.List(['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'])

    landsat_ic_y2d = l5_collection.merge(l7_collection).merge(l8_collection).filterBounds(point).map(add_ndvi).select(
        'ndvi').filterDate(y2d_start, now).map(landsat_avg)
    y2d_plot = landsat_ic_y2d.aggregate_array('avgndvi').getInfo()
    y2d_date = landsat_ic_y2d.aggregate_array('system:time_start').getInfo()
    dates = pd.to_datetime(np.array(y2d_date) * 1e6)

    y2d = pd.DataFrame(y2d_plot)

    y2d["data_values"] = y2d[0]
    y2d["day"] = dates
    y2d["date"] = y2d["day"].dt.strftime("%Y-%m-%d")

    def avg_landsat_month(month_str):
        return landsat_ic.filterMetadata('month', 'equals', month_str).mean()

    test_ic = ee.ImageCollection.fromImages(month_list.map(avg_landsat_month)).map(landsat_avg)

    info_to_plot = test_ic.aggregate_array('avgndvi').getInfo()

    avg = pd.DataFrame(info_to_plot)
    avg['data_values'] = avg[0]

    avg['date'] = [datetime.datetime(year = int(now[:4]), month = avg.index[i]+1, day = 15) for i in avg.index]

    Dict = {'avg': avg, 'y2d': y2d, 'title':"NDVI", ' yaxis': "NO IDEA"}
    print(Dict)

    return Dict