"""Dyson exceptions."""


class DysonInvalidTargetTemperatureException(Exception):
    """Invalid target temperature Exception."""

    CELSIUS = "Celsius"
    FAHRENHEIT = "Fahrenheit"

    def __init__(self, temperature_unit, current_value):
        """Dyson invalid target temperature.

        :param temperature_unit Celsius/Fahrenheit
        :param current_value invalid value
        """
        super(DysonInvalidTargetTemperatureException, self).__init__()
        self._temperature_unit = temperature_unit
        self._current_value = current_value

    @property
    def temperature_unit(self):
        """Temperature unit: Celsius or Fahrenheit."""
        return self._temperature_unit

    @property
    def current_value(self):
        """Return Current value."""
        return self._current_value

    def __repr__(self):
        """Return a String representation."""
        if self.temperature_unit == self.CELSIUS:
            return "{0} is not a valid temperature target. It must be " \
                   "between 1 to 37 inclusive.".format(self._current_value)
        if self.temperature_unit == self.FAHRENHEIT:
            return "{0} is not a valid temperature target. It must be " \
                   "between 34 to 98 inclusive.".format(self._current_value)
