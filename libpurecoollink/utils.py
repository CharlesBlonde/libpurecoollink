"""Utilities for Dyson Pure Hot+Cool link devices."""

from .const import DYSON_PURE_HOT_COOL_LINK_TOUR


def support_heating(product_type):
    """Return True if device_model support heating mode, else False.

    :param product_type Dyson device model
    """
    if product_type in [DYSON_PURE_HOT_COOL_LINK_TOUR]:
        return True
    return False


def printable_fields(fields):
    """Return printable fields.

    :param fields list of tuble with (label, vallue)
    """
    for field in fields:
        yield field[0]+"="+field[1]
