"""Dyson pure Hot+Cool link device."""

import logging

from .dyson_pure_cool_link import DysonPureCoolLink
from .utils import printable_fields

_LOGGER = logging.getLogger(__name__)


class DysonPureHotCoolLink(DysonPureCoolLink):
    """Dyson Pure Hot+Cool device."""

    def _parse_command_args(self, **kwargs):
        """Parse command arguments.

        :param kwargs Arguments
        :return payload dictionary
        """
        data = super()._parse_command_args(**kwargs)
        heat_mode = kwargs.get('heat_mode')
        heat_target = kwargs.get('heat_target')
        focus_mode = kwargs.get('focus_mode')
        f_heat_mode = heat_mode.value if heat_mode \
            else self._current_state.heat_mode
        f_heat_target = heat_target if heat_target \
            else self._current_state.heat_target
        f_fan_focus = focus_mode.value if focus_mode \
            else self._current_state.focus_mode
        data["hmod"] = f_heat_mode
        data["ffoc"] = f_fan_focus
        data["hmax"] = f_heat_target
        return data

    def set_configuration(self, **kwargs):
        """Configure fan.

        :param kwargs: Parameters
        """
        data = self._parse_command_args(**kwargs)
        self.set_fan_configuration(data)

    def __repr__(self):
        """Return a String representation."""
        fields = self._fields()
        return 'DysonPureHotCoolLink(' + ",".join(
            printable_fields(fields)) + ')'
