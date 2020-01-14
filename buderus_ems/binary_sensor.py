"""Platform for sensor integration."""
from homeassistant.const import DEVICE_CLASS_POWER, DEVICE_CLASS_TEMPERATURE, \
                                DEVICE_CLASS_PRESSURE, DEVICE_CLASS_TIMESTAMP, PRESSURE_BAR, \
                                TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.components.binary_sensor import BinarySensorDevice, DEVICE_CLASS_OPENING
from . import DOMAIN, EVENT_UPDATED
import logging

_LOGGER = logging.getLogger(__name__)

# section, name, description, 
ems_sensors = [
    # UBAMonitorFast
    ['uba_fast', 'gasValve1', 'Gas valve stage 1', DEVICE_CLASS_OPENING],
    ['uba_fast', 'gasValve2', 'Gas valve stage 2', DEVICE_CLASS_OPENING],
    ['uba_fast', 'fan', 'Ventilation', None],
    ['uba_fast', 'ignition', 'Ignition', None],
    ['uba_fast', 'boilerPump', 'Boiler pump', None],
    ['uba_fast', 'valveDrinkWater', 'Valve set to drinkwater heating', None],
    ['uba_fast', 'drinkWaterCircPump', 'Drink water circulation pump', None],

    # UBAMonitorWWMessage values
    ['uba_dw', 'dayMode', 'Day Mode', None],
    ['uba_dw', 'singleHeat', 'One shot drinkwater heat', None],
    ['uba_dw', 'thermDesinfect', 'Thermal desinfection', None],
    ['uba_dw', 'heatingEnabled', 'Drinkwater heating', None],
    ['uba_dw', 'reHeat', 'Drinkwater reheating', None],
    ['uba_dw', 'setTempReached', 'Drinkwater temperature okay', None],
    ['uba_dw', 'sensor1Error', 'Drinkwater sensor 1 error', None],
    ['uba_dw', 'sensor2Error', 'Drinkwater sensor 2 error', None],
    ['uba_dw', 'generalError', 'Drinkwater heating error', None],
    ['uba_dw', 'desinfectError', 'Drinkwater desinfection error', None],
    ['uba_dw', 'circDayMode', 'Drinkwater day mode circulation', None],
    ['uba_dw', 'circManual', 'Drinkwater manual circulation', None],
    ['uba_dw', 'circOn', 'Drinkwater enabled', None],
    ['uba_dw', 'heatingNow', 'Drinkwater currently heating', None],

    # HK1MonitorMessage
    ['hk1', 'onOptimize', 'Optimize turn on', None],
    ['hk1', 'offOptimize', 'Optimize turn off', None],
    ['hk1', 'automatic', 'Automatic mode', None],
    ['hk1', 'preferDrinkwater', 'Prefer drink water heating', None],
    ['hk1', 'screedDrying', 'Screed drying', None],
    ['hk1', 'vacationMode', 'Vacation mode', None],
    ['hk1', 'frostProtection', 'Frost protection mode', None],
    ['hk1', 'manual', 'Manual mode', None],
    ['hk1', 'summerMode', 'Summer mode', None],
    ['hk1', 'dayMode', 'Day mode', None],
    ['hk1', 'remoteDisconnected', 'Remote disconnected', None],
    ['hk1', 'remoteError', 'Remote Error', None],
    ['hk1', 'forwardFlowSensorError', 'Forward flow sensor error', None],
    ['hk1', 'maxForwardFlow', 'Maximum forward flow', None],
    ['hk1', 'externalError', 'External error', None],
    ['hk1', 'partyPauseMode', 'Party pause mode', None],
    #['hk1', 'state0', '', None],
    #['hk1', 'state1', '', None],
    #['hk1', 'stateParty', '', None],
    #['hk1', 'statePause', '', None],
    #['hk1', 'state4', '', None],
    #['hk1', 'state5', '', None],
    #['hk1', 'stateVacation', '', None],
    #['hk1', 'stateHoliday', '', None],

    # RCTimeMessage
    #['rc_time', 'dayOfWeek', 'Day of week', None],
    #['rc_time', 'summerTime', 'Summer time', None],
    #['rc_time', 'radioClock', 'Radio clock source', None],
    #['rc_time', 'timeBad', 'Incorrect time', None],
    #['rc_time', 'dateBad', 'incorrect date', None],
    #['rc_time', 'clockRunning', 'Clock enabled', None],
]

def setup_platform(hass, config, add_entities, discovery_info=None):
    sensors = [EmsBinarySensor(hass, sens_def) for sens_def in ems_sensors]
    add_entities(sensors, True)
    _LOGGER.debug('{}: Binary sensors added'.format(DOMAIN))

class EmsBinarySensor(BinarySensorDevice):
    """Representation of a Sensor."""

    def __init__(self, hass, definition):
        """Initialize the sensor."""
        self._state = None
        self._available = False
        self._variable = definition[1]
        self._name = definition[2]
        self._class = definition[3]
        hass.bus.listen(EVENT_UPDATED + '_' + definition[0], self._handle_update)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

#    @property
#    def icon(self):
#        """Return the icon of the sensor."""
#        return self._icon

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return(self._class)

    @property
    def available(self):
        """Return the availability of the sensor."""
        return(self._available)

    @property
    def should_poll(self):
        """Disable polling."""
        return(False)

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return(self._state)

    def _handle_update(self, call):
        try:
            value = call.data[self._variable]
            self._state = value
            self._available = True
            self.schedule_update_ha_state()
        except KeyError as e:
            _LOGGER.error('No value for {} in update data'.format(e))
            self._available = False
