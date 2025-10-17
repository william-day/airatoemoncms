from pyairahome import AiraHome
import requests
import os
import time
import json

AIRA_UUID = os.environ.get('AIRA_UUID')
EMONCMS_URL = os.environ.get('EMONCMS_URL')
EMONCMS_APIKEY = os.environ.get('EMONCMS_APIKEY')
EMONCMS_NODE = os.environ.get('EMONCMS_NODE')


def fix_the_format(additional):
    
    deltaT = additional['sensor_values']['outdoor_unit_supply_temperature'] - additional['sensor_values']['outdoor_unit_return_temperature']
    flowRate = additional['sensor_values']['flow_meter1']
    heatpump_heat = deltaT * 4200 * flowRate / 60 # Watts
    if heatpump_heat < 0:
        heatpump_heat = 0
    
    heatpump_dhw = 0
    heatpump_ch = 0
    
    if additional['megmet_status']['requested_state'] or additional['megmet_status']['current_operation_mode']: # REALLY NEEDS MORE THOUGHT
        if additional['valve_status']['dhw_heating_cooling_valve'] == 'POSITION_DHW':
            heatpump_dhw = 1
        else:
            heatpump_ch = 1
        
    good_format = {
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
        'heatpump_dhwTargetT': 50,
        'immersion_elec': 0, # fix later
        'heatpump_cooling': 0, # fix later
        'heatpump_error': 0 # no idea
        
    }
    
    return good_format


def upload_to_econcms(good_format):
    json_format = json.dumps(good_format)
 
    post_data = {
        'node': EMONCMS_NODE,
        'data': json_format,
        'apikey': EMONCMS_APIKEY
    }
    
    x = requests.post(EMONCMS_URL, data=post_data)

    print(f'Status: {x.status_code} Text: {x.text}')


def main():
    
    # Initialize the library
    aira = AiraHome()
    
    connected = aira.ble.connect_uuid(AIRA_UUID)
    
    if connected:
        print("Connected: Entering upload loop")
        bad_tries = 0
        while True:
            try:
                additional = aira.ble.get_system_check_state()
                good_format = fix_the_format(additional['system_check_state'])
                upload_to_econcms(good_format)
                bad_tries = 0
            except:
                bad_tries += 1
                print(f"EXCEPTION!!! - Bad tries: {bad_tries}")
                if bad_tries > 9:
                    print("TOO MANY FAILURES!! - EXITING!")
                    exit(1)
                    
            time.sleep(5)
    else:
        print("Error: Failed to connect")

    

if __name__ == '__main__':
    main()

