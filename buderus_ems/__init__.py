import threading
from . import ems
import logging
import voluptuous as vol
from homeassistant.const import CONF_DEVICE, EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

PLATFORMS = ['sensor', 'binary_sensor']
DOMAIN = 'buderus_ems'
_LOGGER = logging.getLogger(__name__)
EVENT_UPDATED = 'buderus_ems_received'

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_DEVICE): cv.string})}, extra=vol.ALLOW_EXTRA
)

def setup(hass, config):
    """Set up the EMS parser component"""
    conf = config[DOMAIN]
    buderus_ems = BuderusEms(hass, conf[CONF_DEVICE])

    def _start_ems(_event):
        buderus_ems.start()

    def _stop_ems(_event):
        buderus_ems.stopped.set()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, _start_ems)
    #hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _stop_ems)

    #hass.data[DOMAIN] = buderus_ems

    for platform in PLATFORMS:
        discovery.load_platform(hass, platform, DOMAIN, {}, config)
        _LOGGER.debug('{}: platform {} loaded'.format(DOMAIN, platform))

    return(True)

class BuderusEms(threading.Thread):
    """Handles communication with the EMS bus"""
    def __init__(self, hass, device):
        super().__init__()
        self._available = False
        self._device = device
        self.hass = hass
        self.status = ems.status
        _LOGGER.debug('{}: Initialized'.format(DOMAIN))

    @property
    def available(self):
        """Return the availability of the connection"""
        return self._available

    def run(self):
        _LOGGER.debug('{}: Starting...'.format(DOMAIN))
        try:
            port = ems.open_serial(self._device)
        except Exception as e:
            _LOGGER.error('{}: Could not open device {}: {}'.format(DOMAIN, self._device, e))
            return()

        _LOGGER.debug('{}: Port {} opened, reading...'.format(DOMAIN, port))
        self._available = True
        ems.mainloop(port, self.hass)
