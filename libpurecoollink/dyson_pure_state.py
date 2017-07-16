"""Dyson Pure link devices (Cool and Hot+Cool) states."""

# pylint: disable=too-many-public-methods,too-many-instance-attributes

import json
from .utils import printable_fields


class DysonPureCoolState:
    """Dyson device state."""

    @staticmethod
    def is_state_message(payload):
        """Return true if this message is a Dyson Pure state message."""
        return json.loads(payload)['msg'] in ["CURRENT-STATE", "STATE-CHANGE"]

    @staticmethod
    def _get_field_value(state, field):
        """Get field value."""
        return state[field][1] if isinstance(state[field], list) else state[
            field]

    def __init__(self, payload):
        """Create a new state.

        :param product_type: Product type
        :param payload: Message payload
        """
        json_message = json.loads(payload)
        self._state = json_message['product-state']
        self._fan_mode = self._get_field_value(self._state, 'fmod')
        self._fan_state = self._get_field_value(self._state, 'fnst')
        self._night_mode = self._get_field_value(self._state, 'nmod')
        self._speed = self._get_field_value(self._state, 'fnsp')
        self._oscilation = self._get_field_value(self._state, 'oson')
        self._filter_life = self._get_field_value(self._state, 'filf')
        self._quality_target = self._get_field_value(self._state, 'qtar')
        self._standby_monitoring = self._get_field_value(self._state, 'rhtm')

    @property
    def fan_mode(self):
        """Fan mode."""
        return self._fan_mode

    @property
    def fan_state(self):
        """Fan state."""
        return self._fan_state

    @property
    def night_mode(self):
        """Night mode."""
        return self._night_mode

    @property
    def speed(self):
        """Fan speed."""
        return self._speed

    @property
    def oscillation(self):
        """Oscillation mode."""
        return self._oscilation

    @property
    def filter_life(self):
        """Filter life."""
        return self._filter_life

    @property
    def quality_target(self):
        """Air quality target."""
        return self._quality_target

    @property
    def standby_monitoring(self):
        """Monitor when inactive (standby)."""
        return self._standby_monitoring

    def __repr__(self):
        """Return a String representation."""
        fields = [("fan_mode", self.fan_mode), ("fan_state", self.fan_state),
                  ("night_mode", self.night_mode), ("speed", self.speed),
                  ("oscillation", self.oscillation),
                  ("filter_life", self.filter_life),
                  ("quality_target", self.quality_target),
                  ("standby_monitoring", self.standby_monitoring)]

        return 'DysonPureCoolState(' + ",".join(printable_fields(fields)) + ')'


class DysonEnvironmentalSensorState:
    """Environmental sensor state."""

    @staticmethod
    def is_environmental_state_message(payload):
        """Return true if this message is a state message."""
        json_message = json.loads(payload)
        return json_message['msg'] in ["ENVIRONMENTAL-CURRENT-SENSOR-DATA"]

    @staticmethod
    def __get_field_value(state, field):
        """Get field value."""
        return state[field][1] if isinstance(state[field], list) else state[
            field]

    def __init__(self, payload):
        """Create a new Environmental sensor state.

        :param payload: Message payload
        """
        json_message = json.loads(payload)
        data = json_message['data']
        humidity = self.__get_field_value(data, 'hact')
        self._humidity = 0 if humidity == 'OFF' else int(humidity)
        volatil_copounds = self.__get_field_value(data, 'vact')
        self._volatil_compounds = 0 if volatil_copounds == 'INIT' else int(
            volatil_copounds)
        temperature = self.__get_field_value(data, 'tact')
        self._temperature = 0 if temperature == 'OFF' else float(
            temperature) / 10
        self._dust = int(self.__get_field_value(data, 'pact'))
        sltm = self.__get_field_value(data, 'sltm')
        self._sleep_timer = 0 if sltm == 'OFF' else int(sltm)

    @property
    def humidity(self):
        """Humidity in percent."""
        return self._humidity

    @property
    def volatil_organic_compounds(self):
        """Volatil organic compounds level."""
        return self._volatil_compounds

    @property
    def temperature(self):
        """Temperature in Kelvin."""
        return self._temperature

    @property
    def dust(self):
        """Dust level."""
        return self._dust

    @property
    def sleep_timer(self):
        """Sleep timer."""
        return self._sleep_timer

    def __repr__(self):
        """Return a String representation."""
        fields = [("humidity", str(self.humidity)),
                  ("air quality", str(self.volatil_organic_compounds)),
                  ("temperature", str(self.temperature)),
                  ("dust", str(self.dust)),
                  ("sleep_timer", str(self._sleep_timer))]
        return 'DysonEnvironmentalSensorState(' + ",".join(
            printable_fields(fields)) + ')'


class DysonPureHotCoolState(DysonPureCoolState):
    """Dyson device state."""

    def __init__(self, payload):
        """Create a new Dyson Hot+Cool state.

        :param product_type: Product type
        :param payload: Message payload
        """
        super().__init__(payload)

        self._tilt = DysonPureCoolState._get_field_value(self._state, 'tilt')
        self._fan_focus = DysonPureCoolState._get_field_value(self._state,
                                                              'ffoc')
        self._heat_target = DysonPureCoolState._get_field_value(self._state,
                                                                'hmax')
        self._heat_mode = DysonPureCoolState._get_field_value(self._state,
                                                              'hmod')
        self._heat_state = DysonPureCoolState._get_field_value(self._state,
                                                               'hsta')

    @property
    def tilt(self):
        """Return tilt status."""
        return self._tilt

    @property
    def focus_mode(self):
        """Focus the fan on one stream or spread."""
        return self._fan_focus

    @property
    def heat_target(self):
        """Heat target of the temperature."""
        return self._heat_target

    @property
    def heat_mode(self):
        """Heat mode on or off."""
        return self._heat_mode

    @property
    def heat_state(self):
        """Return heat state."""
        return self._heat_state

    def __repr__(self):
        """Return a String representation."""
        fields = [("fan_mode", self.fan_mode), ("fan_state", self.fan_state),
                  ("night_mode", self.night_mode), ("speed", self.speed),
                  ("oscillation", self.oscillation),
                  ("filter_life", self.filter_life),
                  ("quality_target", self.quality_target),
                  ("standby_monitoring", self.standby_monitoring),
                  ("tilt", self.tilt),
                  ("focus_mode", self.focus_mode),
                  ("heat_mode", self.heat_mode),
                  ("heat_target", self.heat_target),
                  ("heat_state", self.heat_state)]

        return 'DysonHotCoolState(' + ",".join(printable_fields(fields)) + ')'
