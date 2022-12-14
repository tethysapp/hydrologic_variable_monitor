from django.http.response import JsonResponse
from django.shortcuts import render
from tethys_sdk.permissions import login_required
from .ee_auth import *
import json
from django.http import JsonResponse, HttpResponseNotAllowed
from . import ee_auth
import logging
from .ee_tools import ERA5, get_tile_url, GLDAS, CHIRPS, IMERG, NDVI
from .plots import plot_ERA5, plot_GLDAS, plot_IMERG, plot_CHIRPS, plot_NDVI
from .compare import air_temp_compare, precip_compare, surface_temp_compare


# @controller(name='home', url='/', login_required=
# @login_required()
def home(request):
    if not EE_IS_AUTHORIZED:
        return render(request, 'hydro_var_monitor/no_auth_error.html')
    ee_sources = {
        'air_temp': ['GLDAS', 'ERA5'],
        'ndvi': ['Landsat', ],
        'precip': ['GLDAS', 'CHIRPS', 'IMERG', 'ERA5'],
        'soil_moisture': ['GLDAS', ],
        'soil_temperature': ['ERA5', 'GLDAS']
    }
    context = {
        'sources': json.dumps(ee_sources)
    }
    return render(request, 'hydro_var_monitor/home.html', context)


def compare(request):
    response_data = {'success': False}
    try:
        # log.debug(f'GET: {request.GET}')

        region = request.GET.get('region', None)
        var = request.GET.get('variable', None)

        if var == "air_temp":
            dict = air_temp_compare(json.loads(region))

        if var == "precip":
            dict = precip_compare(json.loads(region))

        if var == "soil_temperature":
            dict = surface_temp_compare(json.loads(region))

        response_data.update({
            'success': True,
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'

    return JsonResponse(json.loads(json.dumps(dict)))


# @controller(name='get-map-id', url='/ee/get-map-id', login_required=True)
def get_map_id(request):
    response_data = {'success': False}

    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    try:
        # log.debug(f'GET: {request.GET}')

        region = request.GET.get('region', None)
        sensor = request.GET.get('source', None)
        var = request.GET.get('variable', None)

        if sensor == "ERA5":
            if var == "air_temp":
                band = "temperature_2m"
                vis_params = {"min": 250, "max": 300,
                              "palette": ['009392', '72aaa1', 'b1c7b3', 'f1eac8', 'e5b9ad', 'd98994', 'd0587e']}
            if var == "precip":
                band = "total_precipitation"
                vis_params = {"min": 0, "max": 0.03, "palette": ['00FFFF', '0000FF']}
            if var == "soil_temperature":
                band = "skin_temperature"
                vis_params = {"min": 250, "max": 300,
                              "palette": ['009392', '72aaa1', 'b1c7b3', 'f1eac8', 'e5b9ad', 'd98994', 'd0587e']}

            imgs = ERA5(band)

        if sensor == "GLDAS":
            if var == "precip":
                band = "Rainf_tavg"
                vis_params = {"min": 0, "max": 0.0002, "palette": ['00FFFF', '0000FF']}
            if var == "air_temp":
                band = "Tair_f_inst"
                vis_params = {"min": 206, "max": 328,
                              "palette": ['009392', '72aaa1', 'b1c7b3', 'f1eac8', 'e5b9ad', 'd98994', 'd0587e']}
            if var == "soil_moisture":
                band = "RootMoist_inst"
                vis_params = {"min": 1.99, "max": 48, "palette": ['00FFFF', '0000FF']}
            if var == "soil_temperature":
                band = "AvgSurfT_inst"
                vis_params = {"min": 222, "max": 378,
                              "palette": ['009392', '72aaa1', 'b1c7b3', 'f1eac8', 'e5b9ad', 'd98994', 'd0587e']}
            imgs = GLDAS(band)

        if sensor == "IMERG":
            band = "HQprecipitation"
            vis_params = {"min": 0, "max": 5, "palette": ['00FFFF', '0000FF']}
            imgs = IMERG(band)

        if sensor == "CHIRPS":
            band = "precipitation"
            vis_params = {"min": 0, "max": 150, "palette": ['00FFFF', '0000FF']}
            imgs = CHIRPS(band)

        if sensor == "Landsat":
            vis_params = {"min": -1, "max": 1, "palette": ['blue', 'white', 'green']}
            imgs = NDVI(json.loads(region))
            # print ("in landsat")
        # get the url from specified image and then return it in json
        wurl = get_tile_url(imgs, vis_params)
        response_data.update({
            'success': True,
            'water_url': wurl,
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'

    return JsonResponse(response_data)


# @controller(name='get-plot', url='/ee/get-plot', login_required=True)
def get_plot(request):
    response_data = {'success': False}

    try:
        # log.debug(f'GET: {request.GET}')

        sensor = request.GET.get('source', None)
        var = request.GET.get('variable', None)
        region = request.GET.get('region', None)

        if sensor == "ERA5":
            if var == "air_temp":
                band = "temperature_2m"
                title = "Temperatura del Aire - ERA5"
                yaxis = "temperature in K"
            if var == "precip":
                band = "total_precipitation"
                title = "Acumulados de Precipitaci??n - ERA5"
                yaxis = "mm of precipitaci??n"
            if var == "soil_temperature":
                band = "skin_temperature"
                title = "Temperatura del Suelo- ERA5"
                yaxis = "temperatura in K"
            plot_data = plot_ERA5(json.loads(region), band, title, yaxis)

        if sensor == "GLDAS":
            if var == "precip":
                band = "Rainf_tavg"
                title = "Acumulados de Precipitaci??n- GLDAS"
                yaxis = "mm of precipitaci??n"
            if var == "air_temp":
                band = "Tair_f_inst"
                title = "Temperatura del Aire- GLDAS"
                yaxis = "temperatura in K"
            if var == "soil_moisture":
                band = "RootMoist_inst"
                title = "Humedad del Suelo - GLDAS"
                yaxis = "kg/m^2"
            if var == "soil_temperature":
                band = "AvgSurfT_inst"
                title = "Temperatura del Suelo - GLDAS"
                yaxis = "temperatura in K"
            plot_data = plot_GLDAS(json.loads(region), band, title, yaxis)

        if sensor == "IMERG":
            plot_data = plot_IMERG(json.loads(region))

        if sensor == "CHIRPS":
            plot_data = plot_CHIRPS(json.loads(region))

        if sensor == "Landsat":
            plot_data = plot_NDVI(json.loads(region))

        response_data.update({
            'success': True,
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'
    return JsonResponse(json.loads(json.dumps(plot_data)))
