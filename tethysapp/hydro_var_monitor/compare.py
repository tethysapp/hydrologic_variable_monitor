import datetime
import ee
import pandas as pd
import calendar
from .plots import get_current_date, get_collection
import numpy as np


def precip_compare(region):
    # get needed functions

    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    area = ee.Geometry.Polygon(get_coord["coordinates"])

    def clip_to_bounds(img):
        return img.updateMask(ee.Image.constant(1).clip(area).mask())

    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
            #scale=1e6,
        ))

    def avg_in_bounds(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
        ))


    # get gldas data
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)

    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
    )
    # consider that each day is growing at the average monthly rate
    img_col_avg = ee.ImageCollection(
        [f'users/rachelshaylahuber55/era5_monthly_avg/era5_monthly_{i:02}' for i in range(1, 13)])


    avg_img = img_col_avg.select("total_precipitation").map(avg_gldas)

    avg_df = pd.DataFrame(
        avg_img.aggregate_array('avg_value').getInfo(),
    )
    # consider that each day is growing at the average monthly rate
    date_generated_gldas = pd.date_range(y2d_start, periods=365)
    cum_df_gldas = pd.DataFrame(date_generated_gldas)
    values_list = []
    for date in cum_df_gldas[0]:
        i = 1
        for val in gldas_avg_df["Rainf_tavg"]:
            if date.month == i:
                values_list.append(val * 86400)  # it is a rate per second - 86400 seconds in day convert to per day
            i = i + 1
    cum_df_gldas['val_per_day'] = values_list
    # code will look for columns names 'date' and 'data_values' so rename to those
    cum_df_gldas['date'] = cum_df_gldas[0].dt.strftime("%Y-%m-%d")
    cum_df_gldas["data_values"] = cum_df_gldas['val_per_day'].cumsum()
    gldas_avg_df = cum_df_gldas
    # set date and data values columns that the js code will look for
    avg_df.columns = ["data_values"]
    avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=avg_df.index[i] + 1, day=15) for i in avg_df.index]
    avg_df['date'] = avg_df['datetime'].dt.strftime("%Y-%m-%d")
    avg_df.reset_index(drop=True, inplace=True)
    # precipitation must be cumulatively summer throughout the year
    date_generated_era = pd.date_range(y2d_start, periods=365)
    cum_df_era = pd.DataFrame(date_generated_era)
    values_list = []
    for date in cum_df_era[0]:
        i = 1
        for val in avg_df["data_values"]:
            if date.month == i:
                values_list.append(val)
            i = i + 1
    # multiply by 1000 to convert into mm from meters
    cum_df_era['val_per_day'] = values_list
    cum_df_era['date'] = cum_df_era[0].dt.strftime("%Y-%m-%d")
    cum_df_era["data_values"] = (cum_df_era['val_per_day'] * 1000).cumsum()
    era5_df = cum_df_era
    # get Imerg data
    imerg_1m_ic = ee.ImageCollection(
        [f'users/rachelshaylahuber55/imerg_monthly_avg/imerg_monthly_avg_{i:02}' for i in range(1, 13)])

    imerg_1m_values_ic = imerg_1m_ic.select('HQprecipitation').map(avg_in_bounds)

    imerg_1m_df = pd.DataFrame(
        imerg_1m_values_ic.aggregate_array('avg_value').getInfo(),
    ).dropna()

    date_generated = pd.date_range(y2d_start, periods=365)
    imerg_cum_df = pd.DataFrame(date_generated)

    values_list = []
    for date in imerg_cum_df[0]:
        i = 1
        # print("printing date")
        # print (date)
        for val in imerg_1m_df["HQprecipitation"]:
            if date.month == i:
                values_list.append(val * 24)
            i = i + 1
    # print(values_list)

    imerg_cum_df["val_per_day"] = values_list
    imerg_cum_df["data_values"] = imerg_cum_df["val_per_day"].cumsum()

    imerg_cum_df['date'] = imerg_cum_df[0].dt.strftime("%Y-%m-%d")

    # get chirps
    chirps_pentad_ic = ee.ImageCollection(
        [f'users/rachelshaylahuber55/chirps_monthly_avg/chirps_monthly_avg_{i:02}' for i in range(1, 13)])

    def chirps_avg(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
        ).get('precipitation'))

    days_in_month = np.array([calendar.monthrange(int(now[:4]), i)[1] for i in range(1, 13)])

    chirps_avg_ic = chirps_pentad_ic.select('precipitation').map(clip_to_bounds).map(
        chirps_avg)
    chirps_df = pd.DataFrame(
        chirps_avg_ic.aggregate_array('avg_value').getInfo(),

        columns=['depth', ]
    ).dropna()

    chirps_df['data_values'] = chirps_df['depth'].cumsum() * days_in_month / 5
    chirps_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=chirps_df.index[i] + 1, day=15) for i in
                             chirps_df.index]

    chirps_df['date'] = chirps_df['datetime'].dt.strftime("%Y-%m-%d")

    title = "Precipitation"

    return {'imerg': imerg_cum_df, 'chirps': chirps_df, 'era5': era5_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "mm of precipitation"}


def air_temp_compare(region):
    now, avg_start, y2d_start = get_current_date()

    get_coord = region["geometry"]
    area = ee.Geometry.Polygon(get_coord["coordinates"])

    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
        ))

    # get era5 dataframe
    img_col_avg = ee.ImageCollection(
        [f'users/rachelshaylahuber55/era5_monthly_avg/era5_monthly_{i:02}' for i in range(1, 13)])

    avg_img = img_col_avg.select("temperature_2m").map(avg_gldas)

    era5_avg_df = pd.DataFrame(
        avg_img.aggregate_array('avg_value').getInfo(),
    )

    era5_avg_df.columns = ["data_values"]
    era5_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=era5_avg_df.index[i] + 1, day=15) for i in era5_avg_df.index]
    era5_avg_df['date'] = era5_avg_df['datetime'].dt.strftime("%Y-%m-%d")
    era5_avg_df.reset_index(drop=True, inplace=True)

    # get gldas dataframe
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)

    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
    )
    gldas_avg_df["data_values"] = gldas_avg_df["Tair_f_inst"]
    gldas_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=gldas_avg_df.index[i] + 1, day=15)
                                for i in gldas_avg_df.index]
    gldas_avg_df['date'] = gldas_avg_df['datetime'].dt.strftime("%Y-%m-%d")

    title = "Air Temperature"

    return {'era5': era5_avg_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "temp in K"}


def surface_temp_compare(region):
    now, avg_start, y2d_start = get_current_date()

    get_coord = region["geometry"]
    area = ee.Geometry.Polygon(get_coord["coordinates"])

    # define functions that will be mapped
    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
            scale=1e6,
        ))

    # get era5 data
    img_col_avg = ee.ImageCollection(
        [f'users/rachelshaylahuber55/era5_monthly_avg/era5_monthly_{i:02}' for i in range(1, 13)])
    avg_img = img_col_avg.select("skin_temperature").map(avg_gldas)
    era5_avg_df = pd.DataFrame(
        avg_img.aggregate_array('avg_value').getInfo(),
    )

    era5_avg_df.columns = ["data_values"]
    era5_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=era5_avg_df.index[i] + 1, day=15) for i in
                               era5_avg_df.index]
    era5_avg_df['date'] = era5_avg_df['datetime'].dt.strftime("%Y-%m-%d")
    era5_avg_df.reset_index(drop=True, inplace=True)
    # get gldas data
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)

    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
        # index=np.array(gldas_avg.aggregate_array('month').getInfo()).astype(int),
    )
    gldas_avg_df["data_values"] = gldas_avg_df["AvgSurfT_inst"]
    gldas_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=gldas_avg_df.index[i] + 1, day=15)
                                for i in gldas_avg_df.index]
    gldas_avg_df['date'] = gldas_avg_df['datetime'].dt.strftime("%Y-%m-%d")

    title = "Surface Temperature"
    return {'era5': era5_avg_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "temp in K"}

