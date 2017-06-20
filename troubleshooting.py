from libpurecoollink.dyson import DysonAccount
from libpurecoollink.const import FanSpeed, FanMode, NightMode, Oscillation, \
    FanState, StandbyMonitoring, QualityTarget
import time
from pprint import pprint

#### Variables #####
username = "<email>"
password = "<password>"
language = "<language>"
device_ip = "<ip_address>"
#### End Variables ####

dyson_account = DysonAccount(username, password, language)
dyson_account.login()
devices = dyson_account.devices()


def on_message(message):
    pprint(message)


connected = devices[0].connect(on_message, "192.168.18.103")

if not connected:
    print('Unable to get any data!')
else:
    time.sleep(90)
    devices[0].disconnect()
