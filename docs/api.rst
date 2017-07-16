.. _api:

Developer Interface
===================

.. module:: libpurecoollink.dyson
.. module:: libpurecoollink.dyson_device
.. module:: libpurecoollink.dyson_360_eye
.. module:: libpurecoollink.dyson_pure_cool_link
.. module:: libpurecoollink.dyson_pure_hotcool_link
.. module:: libpurecoollink.dyson_pure_state

This part of the documentation covers all the interfaces of Libpurecoollink.


Classes
-------

Common
~~~~~~

DysonAccount
############

.. autoclass:: libpurecoollink.dyson.DysonAccount
    :members:

NetworkDevice
#############

.. autoclass:: libpurecoollink.dyson_device.NetworkDevice
    :members:

Fan/Purifier devices
~~~~~~~~~~~~~~~~~~~~

DysonPureCoolLink
#################

.. autoclass:: libpurecoollink.dyson_pure_cool_link.DysonPureCoolLink
    :members:
    :inherited-members:

DysonPureHotCoolLink
####################

.. autoclass:: libpurecoollink.dyson_pure_hotcool_link.DysonPureHotCoolLink
    :members:
    :inherited-members:

DysonPureCoolState
##################

.. autoclass:: libpurecoollink.dyson_pure_state.DysonPureCoolState
    :members:

DysonEnvironmentalSensorState
#############################

.. autoclass:: libpurecoollink.dyson_pure_state.DysonEnvironmentalSensorState
    :members:

DysonPureHotCoolState
#####################

.. autoclass:: libpurecoollink.dyson_pure_state.DysonPureHotCoolState
    :members:
    :inherited-members:

Eye 360 robot vacuum device
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dyson360Eye
###########

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360Eye
    :members:
    :inherited-members:

Dyson360EyeState
################

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360EyeState
    :members:

Dyson360EyeTelemetryData
########################

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360EyeTelemetryData
    :members:

Dyson360EyeMapData
##################

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360EyeMapData
    :members:

Dyson360EyeMapGrid
##################

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360EyeMapGrid
    :members:

Dyson360EyeMapGlobal
####################

.. autoclass:: libpurecoollink.dyson_360_eye.Dyson360EyeMapGlobal
    :members:

Exceptions
----------

DysonNotLoggedException
~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: libpurecoollink.exceptions.DysonNotLoggedException

DysonInvalidTargetTemperatureException
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: libpurecoollink.exceptions.DysonInvalidTargetTemperatureException
