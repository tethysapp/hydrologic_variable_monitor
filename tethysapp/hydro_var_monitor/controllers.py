from django.http.response import JsonResponse
from django.shortcuts import render
from tethys_sdk.routing import controller
import json

import ee

from .app import HydroVarMonitor as app


EE_IS_AUTHORIZED = False

try:
    ee.Initialize(ee.ServiceAccountCredentials(None, app.get_custom_setting('ee_auth_token_path')))
    EE_IS_AUTHORIZED = True
except Exception as e:
    print(str(e))


@controller(name='home', url='/', login_required=True)
def ctrl_home(request):
    if not EE_IS_AUTHORIZED:
        return render(request, 'hydro_var_monitor/no_auth_error.html')
    ee_sources = {
        'air_temp': ['GLDAS', 'ERA5'],
        'ndvi': ['Landsat', ],
        'precip': ['GLDAS', 'CHIRPS', 'IMERG', 'ERA5'],
        'soil_moisture': ['GLDAS', ],
        'soil_temp': ['ERA5', ]
    }
    context = {
        'sources': json.dumps(ee_sources)
    }
    return render(request, 'hydro_var_monitor/home.html', context)


@controller(name='get-map-id', url='/ee/get-map-id', login_required=True)
def ctrl_get_map_id(request):
    args = json.loads(request.body.decode())
    return JsonResponse({'url': ''})


@controller(name='get-plot', url='/ee/get-plot', login_required=True)
def ctrl_get_plot(request):
    args = json.loads(request.body.decode())
    return JsonResponse({'plot': ''})
