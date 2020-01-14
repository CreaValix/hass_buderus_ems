"""Platform for sensor integration."""
from homeassistant.const import DEVICE_CLASS_POWER, DEVICE_CLASS_TEMPERATURE, \
                                DEVICE_CLASS_PRESSURE, DEVICE_CLASS_TIMESTAMP, PRESSURE_BAR, \
                                TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from . import DOMAIN, EVENT_UPDATED
import logging

_LOGGER = logging.getLogger(__name__)

PERCENT = '%'
CURRENT_MILLIAMPS = 'mA'
LITERS_PER_MINUTE = 'l/min'
DURATION_MINUTES = 'min'

# section, name, description, 
ems_sensors = [
    # UBAMonitorFast
    ['uba_fast', 'flowTempSet', 'Forward flow set temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_fast', 'flowTempIs', 'Forward flow current temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_fast', 'burnPowSet', 'Burner set power', None, PERCENT],
    ['uba_fast', 'burnPowIs', 'Burner current power', None, PERCENT],
    #['uba_fast', 'gasValve1', 'Gas valve stage 1', None],
    #['uba_fast', 'gasValve2', 'Gas valve stage 2', None],
    #['uba_fast', 'fan', 'Ventilation', None],
    #['uba_fast', 'ignition', 'Ignition', None],
    #['uba_fast', 'boilerPump', 'Boiler pump', None],
    #['uba_fast', 'valveDrinkWater', 'Valve set to drinkwater heating', None],
    #['uba_fast', 'drinkWaterCircPump', 'Dring water circulation pump', None],
    ['uba_fast', 'boilerTemp', 'Boiler current temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_fast', 'drinkWaterTemp', 'Drinkwater temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_fast', 'flowReturnTemp', 'Return flow temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_fast', 'flameCurrent', 'Flame current', DEVICE_CLASS_POWER, CURRENT_MILLIAMPS],
    ['uba_fast', 'systemPressure', 'System water pressure', DEVICE_CLASS_PRESSURE, PRESSURE_BAR],
    #['uba_fast', 'serviceCode', 'Service code', None],
    #['uba_fast', 'errorCode', 'Error code', None],
    ['uba_fast', 'intakeTemp', 'Intake air temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],

    # UBAMonitorSlow
    ['uba_slow', 'outsideTemp', 'Outside temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_slow', 'boilerTemp', 'Boiler temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_slow', 'exhaustTemp', 'Exhaust temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_slow', 'pumpMod', 'Pump modulation', None, PERCENT],
    ['uba_slow', 'burnStarts', 'Burner starts', None, None],
    ['uba_slow', 'burnOperTot', 'Burner operation time', None, DURATION_MINUTES],
    ['uba_slow', 'burnOperStage2', 'Burner stage 2 operation time', None, DURATION_MINUTES],
    ['uba_slow', 'burnOperHeat', 'Burner heating time', None, DURATION_MINUTES],
    ['uba_slow', 'burnOperDrinkWater', 'Burner drinkwater operation time', None, DURATION_MINUTES],

    # UBAMonitorWWMessage values
    ['uba_dw', 'tempSet', 'Drinkwater set temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_dw', 'sensor1tempIs', 'Drinkwater current temperature sensor 1', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_dw', 'sensor2TempIs', 'Drinkwater current temperature sensor 1', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    #['uba_dw', 'dayMode', 'Day Mode', None, None],
    #['uba_dw', 'singleHeat', 'One shot drinkwater heat', None, None],
    #['uba_dw', 'thermDesinfect', 'Thermal desinfection', None, None],
    #['uba_dw', 'heatingEnabled', 'Drinkwater heating enabled', None, None],
    #['uba_dw', 'reHeat', 'Drinkwater reheating enabled', None, None],
    #['uba_dw', 'setTempReached', 'Drinkwater temperature okay', None, None],
    #['uba_dw', 'sensor1Error', 'Drinkwater sensor 1 error', None, None],
    #['uba_dw', 'sensor2Error', 'Drinkwater sensor 2 error', None, None],
    #['uba_dw', 'generalError', 'Drinkwater heating error', None, None],
    #['uba_dw', 'desinfectError', 'Drinkwater desinfection error', None, None],
    #['uba_dw', 'circDayMode', 'Drinkwater day mode circulation', None, None],
    #['uba_dw', 'circManual', 'Drinkwater manual circulation', None, None],
    #['uba_dw', 'circOn', 'Drinkwater enabled', None, None],
    #['uba_dw', 'heatingNow', 'Drinkwater currently heating', None, None],
    ['uba_dw', 'systemType', 'Drinkwater system type', None, None],
    ['uba_dw', 'currentFlow', 'Drinkwater current flow', None, LITERS_PER_MINUTE],
    ['uba_dw', 'heatingTime', 'Drinkwater heating time', None, DURATION_MINUTES],
    ['uba_dw', 'heatingRuns', 'Drinkwater heating cycles', None, None],

    # HK1MonitorMessage
    #['hk1', 'onOptimize', '', None, None],
    #['hk1', 'offOptimize', '', None, None],
    #['hk1', 'automatic', '', None, None],
    #['hk1', 'preferDrinkwater', '', None, None],
    #['hk1', 'screedDrying', '', None, None],
    #['hk1', 'vacationMode', '', None, None],
    #['hk1', 'frostProtection', '', None, None],
    #['hk1', 'manual', '', None, None],
    #['hk1', 'summerMode', '', None, None],
    #['hk1', 'dayMode', '', None, None],
    #['hk1', 'remoteDisconnected', '', None, None],
    #['hk1', 'remoteError', '', None, None],
    #['hk1', 'forwardFlowSensorError', '', None, None],
    #['hk1', 'maxForwardFlow', '', None, None],
    #['hk1', 'externalError', '', None, None],
    #['hk1', 'partyPauseMode', '', None, None],
    ['hk1', 'roomTempSet', 'HC1 Room set temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['hk1', 'roomTempIs', 'HC1 Room current temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    #['hk1', 'onOptimizeTime', 'HC1 Turn on optimization time', None, DURATION_MINUTES],
    #['hk1', 'offOptimizeTime', 'HC1 Turn off optimization time', None, DURATION_MINUTES],
    #['hk1', 'heatingCurve10Deg', '', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    #['hk1', 'heatingCurve0Deg', '', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    #['hk1', 'heatingCurveMinus10Deg', '', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    #['hk1', 'roomTempAdaptionTime', 'HC1 Room temperature adaption time', None, TEMP_CELSIUS],
    #['hk1', 'requestedBoilerPower', 'HC1 Requested boiler power', None, PERCENT],
    #['hk1', 'state0', '', None, None],
    #['hk1', 'state1', '', None, None],
    #['hk1', 'stateParty', '', None, None],
    #['hk1', 'statePause', '', None, None],
    #['hk1', 'state4', '', None, None],
    #['hk1', 'state5', '', None, None],
    #['hk1', 'stateVacation', '', None, None],
    #['hk1', 'stateHoliday', '', None, None],
    ['hk1', 'calculatedForwardTemp', 'HC1 Calculated forward flow temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],

    # RCTimeMessage
    #['rc_time', 'time', 'System time', DEVICE_CLASS_TIMESTAMP, None],
    #['rc_time', 'dayOfWeek', 'Day of week', None, None],
    #['rc_time', 'summerTime', 'Summer time', None, None],
    #['rc_time', 'radioClock', 'Radio clock source', None, None],
    #['rc_time', 'timeBad', 'Incorrect time', None, LITERS_PER_MINUTE],
    #['rc_time', 'dateBad', 'incorrect date', None, DURATION_MINUTES],
    #['rc_time', 'clockRunning', 'Clock enabled', None, None],

    # UBASollwerte
    ['uba_setvalues', 'boilerTempSet', 'Boiler set temperature', DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS],
    ['uba_setvalues', 'requestedPowerHeating', 'Requested heating power', None, PERCENT],
    ['uba_setvalues', 'requestedPowerDrinkwater', 'Requested drinkwater power', None, PERCENT],
]

def setup_platform(hass, config, add_entities, discovery_info=None):
    #data = hass.data[DOMAIN]
    sensors = [EmsSensor(hass, sens_def) for sens_def in ems_sensors]
    add_entities(sensors, True)
    _LOGGER.debug('{}: Sensors added'.format(DOMAIN))

class EmsSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, definition):
        """Initialize the sensor."""
        self._state = None
        self._available = False
        self._value = definition[1]
        self._name = definition[2]
        self._class = definition[3]
        self._unit = definition[4]
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
    def state(self):
        """Return the state of the sensor."""
        return(self._state)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return(self._unit)

    def _handle_update(self, call):
        try:
            value = call.data[self._value]
            self._state = value
            self._available = True
            self.schedule_update_ha_state()
        except KeyError as e:
            _LOGGER.error('No value for {} in update data'.format(e))
            self._available = False
