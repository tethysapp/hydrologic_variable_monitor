import datetime
import ee
import pandas as pd
import calendar
from .plots import get_current_date, get_collection
import numpy as np


def precip_compare(region):
    # get needed functions
    def get_val_at_xypoint(img):
        # reduction function
        temp = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            maxPixels=1e12,
        )
        # set the result as a metadata property in the image
        return img.set(temp)

    print("past get cal")

    def get_df(band_name, img_col, region):
        era_df = img_col.select(band_name)
        era_with_property = era_df.map(get_val_at_xypoint)

        array_of_values = era_with_property.aggregate_array(band_name).getInfo()
        array_of_datetime_values = era_with_property.aggregate_array('system:time_start').getInfo()

        datetime = pd.to_datetime(np.array(array_of_datetime_values) * 1e6)
        df = pd.DataFrame(array_of_values, index=datetime)
        df['day'] = pd.to_datetime(df.index)
        df['day'] = df['day'].dt.strftime('%m-%d')
        return df.groupby('day').mean()

    def clip_to_bounds(img):
        return img.updateMask(ee.Image.constant(1).clip(point).mask())

    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=1e6,
        ))

    def avg_in_bounds(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
        ))

    def chirps_avg(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
        ).get('precipitation'))

    now, avg_start, y2d_start = get_current_date()
    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])

    # get gldas data
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)

    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
    )
    # consider that each day is growing at the average monthly rate
    date_generated = pd.date_range(y2d_start, periods=365)
    cum_df = pd.DataFrame(date_generated)
    values_list = []
    for date in cum_df[0]:
        i = 1
        for val in gldas_avg_df["Rainf_tavg"]:
            if date.month == i:
                values_list.append(val * 86400)  # it is a rate per second - 86400 seconds in day convert to per day
            i = i + 1
    cum_df['val_per_day'] = values_list
    # code will look for columns names 'date' and 'data_values' so rename to those
    cum_df['date'] = cum_df[0].dt.strftime("%Y-%m-%d")
    cum_df["data_values"] = cum_df['val_per_day'].cumsum()
    gldas_avg_df = cum_df

    # get era5 data
    era5_col = get_collection("ECMWF/ERA5_LAND/MONTHLY", point, avg_start, now)
    era5_df = get_df("total_precipitation", era5_col, point)
    cum_df_era5 = pd.DataFrame(date_generated)
    values_list_era5 = []

    # print(cum_df_era5[0])
    for date in cum_df_era5[0]:
        i = 1
        # print(date)
        for val in era5_df[0]:
            if date.month == i:
                values_list_era5.append(val * 1000)  # in m so convert to mm
            i = i + 1

    cum_df_era5['val_per_day'] = values_list_era5
    cum_df_era5['date'] = cum_df_era5[0].dt.strftime("%Y-%m-%d")
    cum_df_era5["data_values"] = cum_df_era5['val_per_day'].cumsum()
    era5_df = cum_df_era5

    # get Imerg data
    imerg_1m_ic = ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V06")
    imerg_1m_values_ic = imerg_1m_ic.select('precipitation').map(avg_in_bounds)

    imerg_1m_df = pd.DataFrame(
        imerg_1m_values_ic.aggregate_array('avg_value').getInfo(),
        index=pd.to_datetime(np.array(imerg_1m_values_ic.aggregate_array('system:time_start').getInfo()) * 1e6, )
    ).dropna()

    # depth = mm/hr * days_in_month * hours_in_day
    imerg_1m_df['precip_depth'] = imerg_1m_df['precipitation'] * np.array(
        [calendar.monthrange(i.year, i.month)[1] * 24 for i in imerg_1m_df.index])

    # group
    imerg_mon_avg_df = imerg_1m_df.groupby(imerg_1m_df.index.month).mean()
    imerg_mon_avg_df['data_values'] = imerg_mon_avg_df['precip_depth'].cumsum()
    imerg_mon_avg_df['datetime'] = [
        datetime.datetime(year=int(now[:4]), month=i, day=calendar.monthrange(int(now[:4]), i)[1]) for i in
        imerg_mon_avg_df.index]
    imerg_mon_avg_df['date'] = imerg_mon_avg_df['datetime'].dt.strftime("%Y-%m-%d")

    # get chirps
    chirps_pentad_ic = ee.ImageCollection('UCSB-CHG/CHIRPS/PENTAD')
    days_in_month = np.array([calendar.monthrange(int(now[:4]), i)[1] for i in range(1, 13)])
    end_of_month_datetimes = np.array(
        [datetime.datetime(year=int(now[:4]), month=i, day=calendar.monthrange(int(now[:4]), i)[1]) for i in
         range(1, 13)])

    chirps_avg_ic = chirps_pentad_ic.filterDate(avg_start, now).select('precipitation').map(clip_to_bounds).map(
        chirps_avg)
    chirps_df = pd.DataFrame(
        chirps_avg_ic.aggregate_array('avg_value').getInfo(),
        index=pd.to_datetime(np.array(chirps_avg_ic.aggregate_array('system:time_start').getInfo()) * 1e6),
        columns=['depth', ]
    ).dropna()

    chirps_monthly_df = chirps_df.groupby(chirps_df.index.strftime('%m')).mean()
    chirps_monthly_df.index = chirps_monthly_df.index.astype(int)
    chirps_monthly_df['data_values'] = chirps_monthly_df['depth'].cumsum() * days_in_month / 5
    chirps_monthly_df['datetime'] = end_of_month_datetimes
    chirps_monthly_df = pd.concat(
        [pd.DataFrame([[0, 0, datetime.datetime(int(now[:4]), 1, 1)], ], columns=chirps_monthly_df.columns),
         chirps_monthly_df])
    chirps_monthly_df['date'] = chirps_monthly_df['datetime'].dt.strftime("%Y-%m-%d")

    title = "Precipitation"

    Dict = {'imerg': imerg_mon_avg_df, 'chirps': chirps_monthly_df, 'era5': era5_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "mm of precipitation"}

    return (Dict)


def air_temp_compare(region):
    now, avg_start, y2d_start = get_current_date()

    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])

    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=1e6,
        ))

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
        print('check')

        array_of_values = era_with_property.aggregate_array(band_name).getInfo()
        array_of_datetime_values = era_with_property.aggregate_array('system:time_start').getInfo()

        datetime = pd.to_datetime(np.array(array_of_datetime_values) * 1e6)
        df = pd.DataFrame(array_of_values, index=datetime)
        df['day'] = pd.to_datetime(df.index)
        df['day'] = df['day'].dt.strftime('%m-%d')
        return df.groupby('day').mean()

    # get era5 dataframe
    img_col_avg = get_collection("ECMWF/ERA5_LAND/MONTHLY", point, avg_start, now)
    era5_avg_df = get_df("temperature_2m", img_col_avg, point)
    print(era5_avg_df)

    era5_avg_df.columns = ["data_values"]
    era5_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=int(i[:2]), day=15) for i in
                               era5_avg_df.index]
    era5_avg_df['date'] = era5_avg_df['datetime'].dt.strftime("%Y-%m-%d")
    era5_avg_df.reset_index(drop=True, inplace=True)
    print(era5_avg_df)

    # get gldas dataframe
    gldas_monthly = ee.ImageCollection(
        [f'users/rachelshaylahuber55/gldas_monthly/gldas_monthly_avg_{i:02}' for i in range(1, 13)])
    gldas_monthly = gldas_monthly.map(avg_gldas)

    print("made image collection")
    print(gldas_monthly.first().bandNames().getInfo())
    gldas_avg_df = pd.DataFrame(
        gldas_monthly.aggregate_array('avg_value').getInfo(),
    )
    gldas_avg_df["data_values"] = gldas_avg_df["Tair_f_inst"]
    gldas_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=gldas_avg_df.index[i] + 1, day=15)
                                for i in gldas_avg_df.index]
    gldas_avg_df['date'] = gldas_avg_df['datetime'].dt.strftime("%Y-%m-%d")
    print(gldas_avg_df)

    title = "Air Temperature"

    Dict = {'era5': era5_avg_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "temp in K"}

    return (Dict)


def surface_temp_compare(region):
    now, avg_start, y2d_start = get_current_date()

    get_coord = region["geometry"]
    point = ee.Geometry.Point(get_coord["coordinates"])
    print("insurface")

    # define functions that will be mapped
    def avg_gldas(img):
        return img.set('avg_value', img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=1e6,
        ))

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

        array_of_values = era_with_property.aggregate_array(band_name).getInfo()
        array_of_datetime_values = era_with_property.aggregate_array('system:time_start').getInfo()

        datetime = pd.to_datetime(np.array(array_of_datetime_values) * 1e6)
        df = pd.DataFrame(array_of_values, index=datetime)
        df['day'] = pd.to_datetime(df.index)
        df['day'] = df['day'].dt.strftime('%m-%d')
        return df.groupby('day').mean()

    # get era5 data
    img_col_avg = get_collection("ECMWF/ERA5_LAND/MONTHLY", point, avg_start, now)
    era5_avg_df = get_df("skin_temperature", img_col_avg, point)

    era5_avg_df.columns = ["data_values"]
    era5_avg_df['datetime'] = [datetime.datetime(year=int(now[:4]), month=int(i[:2]), day=15) for i in
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
    Dict = {'era5': era5_avg_df, 'gldas': gldas_avg_df,
            'title': title, 'yaxis': "temp in K"}

    return (Dict)
