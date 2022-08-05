import ee
from .app import HydroVarMonitor as app

try:
    import collections
    collections.Callable = collections.abc.Callable
    ee.Initialize(ee.ServiceAccountCredentials(None, app.get_custom_setting('ee_auth_token_path')))
    EE_IS_AUTHORIZED = True
except Exception as e:
    EE_IS_AUTHORIZED = False
    print(e)