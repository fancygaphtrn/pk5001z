"""
Support for reading pk5001z DSL modem data/

configuration.yaml

sensor:
  - platform: pk5001z
    host: 192.168.0.1
    port: 80
    username: USERID
    password: PASSWORD
    scan_interval: 3000
"""
import logging
import requests
import json
from datetime import timedelta
import homeassistant.util.dt as dt_util
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
        CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT,
        CONF_RESOURCES
    )
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

BASE_URL = 'http://{0}:{1}{2}'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)

SENSOR_PREFIX = 'pk5001z'
SENSOR_TYPES = {
    'upload': ['Upload', 'Mbps', 'mdi:arrow-up'],
    'download': ['Download', 'Mbps', 'mdi:arrow-down'],
    'dsl_status': ['DSL Status', '', 'mdi:check'],
    'internet_status': ['Internet Status', '', 'mdi:check'],
    'modem_ip': ['Modem IP Address', '', 'mdi:check'],
    'remote_ip': ['Remote IP Address', '', 'mdi:check'],
    'ipv4_link_uptime': ['IPv4 Link Uptime', '', 'mdi:check'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_RESOURCES, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_PORT, default=80): cv.positive_int,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the pk5001z sensors."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    try:
        data = Pk5001zData(host, port, username, password)
    except RunTimeError:
        _LOGGER.error("Pk5001z: Unable to connect fetch data from Pk5001z %s:%s",
                      host, port)
        return False

    entities = []

    for resource in SENSOR_TYPES:
        sensor_type = resource.lower()

        entities.append(Pk5001zSensor(data, sensor_type))
    
    _LOGGER.debug("Pk5001z: entities = %s", entities)
    add_entities(entities)


# pylint: disable=abstract-method
class Pk5001zData(object):
    """Representation of a Pk5001z."""

    def __init__(self, host, port, username, password):
        """Initialize the Pk5001z."""
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self.data = None
        self._backoff = dt_util.utcnow()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the data from the Pk5001z."""

        _LOGGER.debug("Pk5001z: Backoff = %i", self._backoff - dt_util.utcnow())
        if self._backoff > dt_util.utcnow():
            return

        loginurl = BASE_URL.format(
                    self._host, self._port,
                    '/login.cgi'
        )
        dataurl = BASE_URL.format(
                    self._host, self._port,
                    '/GetWANDSLInfo.cgi'
        )
        login_payload = payload = {'loginSubmitValue':'1','admin_username':self._username,'admin_password':self._password}

        try:
            self.data = None
            s = requests.Session()
            resp = s.post(loginurl, data=login_payload)
            if resp.status_code == 200:
                _LOGGER.debug("Pk5001z: login success")
                data = s.get(dataurl)
                if data.status_code == 200:
                    values = data.text.split('|')
                    _LOGGER.debug("Pk5001z: values %i", len(values))
                    if len(values) == 55:
                        _LOGGER.debug("Pk5001z: data success")
                        self.data =  data.text
                    else:
                        _LOGGER.debug("Pk5001z: data failed")
                else:
                    _LOGGER.debug("Pk5001z: data failed")
            else:
                _LOGGER.debug("Pk5001z: login failed")
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Pk5001z: No route to device %s", dataurl)
            self.data = None
            self._backoff = dt_util.utcnow() + timedelta(seconds=60)
            
        _LOGGER.debug("Pk5001z: Data = %s", self.data)


class Pk5001zSensor(Entity):
    """Representation of a Pk5001z sensor from the Pk5001z."""

    def __init__(self, data, sensor_type):
        """Initialize the sensor."""
        self.data = data
        self.type = sensor_type
        self.entity_id = ENTITY_ID_FORMAT.format(SENSOR_PREFIX + "_" + sensor_type)
        self._name = SENSOR_TYPES[self.type][0]
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self._state = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data and use it to update our sensor state."""
        self.data.update()
        _LOGGER.debug("Pk5001z: SensorData = %s", self.data.data)
        _LOGGER.debug("Pk5001z: type = %s", self.type)

        """['CONNECTED', '', 'IPoE via DHCP', '', 'N/A', '', 'N/A', 'N/A', 'N/A', '10M:40S', '', '15354', '15595', '', '26M:54S', '', '1500', '', '1460', '', '71.219.123.120', '', '205.171.2.65', '', '205.171.3.65', '', '71.219.123.254', '', '25M:42S', '', 'CONNECTED', '', '0.604', '', '1.792', '', '255.255.255.0', '', 'Disabled', '', 'N/A', '', 'N/A', '', 'N/A', '', '64', '', 'N/A', '', '', '', '', '', 'N/A\r\n']"""
        
        if self.data.data == None:
            if self.type == 'upload':
                self._state = 0
            elif self.type == 'download':
                self._state = 0
            else:
                self._state = "Unknown"
        else:
            values = self.data.data.split('|')
            
            if self.type == 'upload':
                self._state = values[32]
            if self.type == 'download':
                self._state = values[34]
            if self.type == 'dsl_status':
                self._state = values[30]
            if self.type == 'internet_status':
                self._state = values[0]
            if self.type == 'modem_ip':
                self._state = values[20]
            if self.type == 'remote_ip':
                self._state = values[26]
            if self.type == 'ipv4_link_uptime':
                self._state = values[28]
