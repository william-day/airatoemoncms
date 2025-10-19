from pyairahome import AiraHome
from pyairahome.utils.exceptions import BLEConnectionError
import requests
import os
import time
import json
import logging

AIRA_UUID = os.environ.get('AIRA_UUID')
AIRA_DHW_TARGET_TEMP = os.environ.get('AIRA_DHW_TARGET_TEMP', 55)
EMONCMS_UPLOAD_MAXRETRIES = int(os.environ.get('EMONCMS_UPLOAD_MAXRETRIES', 5))
EMONCMS_UPLOAD_WAITTIME = int(os.environ.get('EMONCMS_UPLOAD_WAITTIME', 5))
EMONCMS_URL = os.environ.get('EMONCMS_URL')
EMONCMS_APIKEY = os.environ.get('EMONCMS_APIKEY')
EMONCMS_NODE = os.environ.get('EMONCMS_NODE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def calc_heatpump_heat(deltaT, flowRate):
    heat = deltaT * 4200 * flowRate / 60 # Watts
    if heat < 0:
        heat = 0
    return heat


def process_to_emoncms_format(additional):
    # Calculate heatpump heat output but only works without immersion booster
    deltaT = additional['sensor_values']['outdoor_unit_supply_temperature'] - additional['sensor_values']['outdoor_unit_return_temperature']
    flowRate = additional['sensor_values']['flow_meter1']
    heatpump_heat = calc_heatpump_heat(deltaT, flowRate)

    heatpump_dhw = 0
    heatpump_ch = 0
    
    immersion_elec = 0
    if additional['inline_heater_status']['is_active']:
        immersion_elec = additional['energy_calculation']['current_electrical_power_w']
        heatpump_heat = additional['energy_calculation']['current_electrical_power_w']

    if additional['megmet_status']['requested_state'] or additional['megmet_status']['current_operation_mode']: # REALLY NEEDS MORE THOUGHT
        if additional['valve_status']['dhw_heating_cooling_valve'] == 'POSITION_DHW':
            heatpump_dhw = 1
        else:
            heatpump_ch = 1
    elif immersion_elec > 0:
        heatpump_dhw = 1
        
    emoncms_format = {
        'heatpump_elec': additional['energy_calculation']['current_electrical_power_w'],
        'heatpump_heat': heatpump_heat,
        'heatpump_flowT': additional['sensor_values']['outdoor_unit_supply_temperature'],
        'heatpump_returnT': additional['sensor_values']['outdoor_unit_return_temperature'],
        'heatpump_outsideT': additional['sensor_values']['outdoor_unit_ambient_temperature'],
        'heatpump_roomT': additional['sensor_values']['indoor_unit_room_temperature_zone1'],
        'heatpump_targetT': additional['sensor_values']['indoor_unit_room_temperature_zone1'],
        'heatpump_flowrate': flowRate,
        'heatpump_dhw': heatpump_dhw, # non-zero when running
        'heatpump_ch': heatpump_ch, # non-zero when running
        'heatpump_dhwT': additional['sensor_values']['indoor_unit_dhw_tank_temperature'],
        'heatpump_dhwTargetT': AIRA_DHW_TARGET_TEMP, # from env var
        'immersion_elec': immersion_elec # watts
    }
    
    return emoncms_format


def upload_to_emoncms(good_format):
    json_format = json.dumps(good_format)
 
    post_data = {
        'node': EMONCMS_NODE,
        'data': json_format,
        'apikey': EMONCMS_APIKEY
    }
    
    logger.debug(f'Posting to EmonCMS URL: {EMONCMS_URL} Data: {post_data}')

    x = requests.post(EMONCMS_URL, data=post_data)

    logger.debug(f'EmonCMS response code: {x.status_code} Text: {x.text}')
    if x.status_code != 200:
        raise Exception(f"Failed to post to EmonCMS - Response code: {x.status_code} Text: {x.text}")


def main():
    
    # Initialize the library
    aira = AiraHome()
    
    connected = aira.ble.connect_uuid(AIRA_UUID)
    
    if connected:
        logger.info("Connected: Entering upload loop")
        bad_tries = 0
        while True:
            try:
                additional = aira.ble.get_system_check_state()
                emoncms_format = process_to_emoncms_format(additional['system_check_state'])
                upload_to_emoncms(emoncms_format)
                bad_tries = 0

            except BLEConnectionError as e:
                # this means there is a connection error, meaning aira is probably disconnected
                time.sleep(5) # wait some time
                aira.ble.connect() # reconnect

                bad_tries += 1
                logging.warning(f"Exception {e} occurred - count of bad tries: {bad_tries}")
                if bad_tries > EMONCMS_UPLOAD_MAXRETRIES:
                    logger.critical("Too many failures - exiting")
                    exit(1)

            except Exception as e:
                bad_tries += 1
                logging.warning(f"Exception {e} occurred - count of bad tries: {bad_tries}")
                if bad_tries > EMONCMS_UPLOAD_MAXRETRIES:
                    logger.critical("Too many failures - exiting")
                    exit(1)

            time.sleep(EMONCMS_UPLOAD_WAITTIME)
    else:
        logger.critical("Failed to connect to Aira device")


if __name__ == '__main__':
    main()

