"""Dyson Pure Cool Link constants."""

from enum import Enum
from .exceptions import DysonInvalidTargetTemperatureException as DITTE

DYSON_PURE_COOL_LINK_TOUR = "475"
DYSON_PURE_COOL_LINK_DESK = "469"
DYSON_PURE_HOT_COOL_LINK_TOUR = "455"


class FanMode(Enum):
    """Fan mode."""

    OFF = 'OFF'
    FAN = 'FAN'
    AUTO = 'AUTO'


class Oscillation(Enum):
    """Oscillation."""

    OSCILLATION_ON = 'ON'
    OSCILLATION_OFF = 'OFF'


class NightMode(Enum):
    """Night mode."""

    NIGHT_MODE_ON = 'ON'
    NIGHT_MODE_OFF = 'OFF'


class FanSpeed(Enum):
    """Fan Speed."""

    FAN_SPEED_1 = '0001'
    FAN_SPEED_2 = '0002'
    FAN_SPEED_3 = '0003'
    FAN_SPEED_4 = '0004'
    FAN_SPEED_5 = '0005'
    FAN_SPEED_6 = '0006'
    FAN_SPEED_7 = '0007'
    FAN_SPEED_8 = '0008'
    FAN_SPEED_9 = '0009'
    FAN_SPEED_10 = '0010'
    FAN_SPEED_AUTO = 'AUTO'


class FanState(Enum):
    """Fan State."""

    FAN_OFF = "OFF"
    FAN_ON = "FAN"


class QualityTarget(Enum):
    """Quality Target for air."""

    QUALITY_NORMAL = "0004"
    QUALITY_HIGH = "0003"
    QUALITY_BETTER = "0001"


class StandbyMonitoring(Enum):
    """Monitor air quality when on standby."""

    STANDBY_MONITORING_ON = "ON"
    STANDBY_MONITORING_OFF = "OFF"


class FocusMode(Enum):
    """Fan operates in a focused stream or wide spread."""

    FOCUS_OFF = "OFF"
    FOCUS_ON = "ON"


class TiltState(Enum):
    """Indicates if device is tilted."""

    TILT_TRUE = "TILT"
    TILT_FALSE = "OK"


class HeatMode(Enum):
    """Heat mode for the fan."""

    HEAT_OFF = "OFF"
    HEAT_ON = "HEAT"


class HeatState(Enum):
    """Heating State."""

    HEAT_STATE_OFF = "OFF"
    HEAT_STATE_ON = "HEAT"


class HeatTarget:
    """Heat Target for fan. Note dyson uses kelvin as the temperature unit."""

    @staticmethod
    def celsius(temperature):
        """Convert the given int celsius temperature to string in Kelvin.

        :param temperature temperature in celsius between 1 to 37 inclusive.
        """
        if temperature < 1 or temperature > 37:
            raise DITTE(DITTE.CELSIUS, temperature)
        return str((int(temperature) + 273) * 10)

    @staticmethod
    def fahrenheit(temperature):
        """Convert the given int fahrenheit temperature to string in Kelvin.

        :param temperature temperature in fahrenheit between 34 to 98
                            inclusive.
        """
        if temperature < 34 or temperature > 98:
            raise DITTE(DITTE.FAHRENHEIT, temperature)
        return str(int((int(temperature) + 459.67) * 5/9) * 10)


class ResetFilter(Enum):
    """Reset the filter status / new filter."""

    RESET_FILTER = "RSTF"
    DO_NOTHING = "STET"
