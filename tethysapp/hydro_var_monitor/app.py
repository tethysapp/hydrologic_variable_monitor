from tethys_sdk.base import TethysAppBase
from tethys_sdk.app_settings import CustomSetting


class HydroVarMonitor(TethysAppBase):
    """
    Tethys app class for Hydrologic Trends Monitor.
    """

    name = 'Hydrologic Variable Monitor'
    description = 'View maps and plots of hydrologic cycle variables recorded by satellites and global models'
    package = 'hydro_var_monitor'
    index = 'home'
    icon = f'{package}/images/icon.gif'
    root_url = 'hydro-var-monitor'
    color = '#6DA8D9'
    tags = ['remote sensing', 'earth engine', 'hydrological cycle', 'essential water variables', 'geoglows toolbox']
    enable_feedback = False
    feedback_emails = []

    def custom_settings(self):
        return (
            CustomSetting(
                name='ee_auth_token_path',
                type=CustomSetting.TYPE_STRING,
                description='Path to an earth engine service account auth token',
                required=False
            ),
        )
