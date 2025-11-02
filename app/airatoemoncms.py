from pyairahome import AiraHome
from pyairahome.utils.exceptions import BLEConnectionError
import requests
import os
import time
import json
import logging
import yaml


LOGLEVEL = os.environ.get('AIRATOEMONCMS_LOGLEVEL', 'INFO').upper()
CONFIG_FILEPATH = '/config/airatoemoncms.yml'
LOGS_FILEPATH = '/logs/airatoemoncms.log'

# We don't want to continue heat calcs if heatpump is not running for a while
heatpump_hold_running = 0

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=LOGLEVEL,
    filename=LOGS_FILEPATH,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def recursive_get(d: dict, keys: list[str]):
    if not keys:
        return d
    if not isinstance(d, dict):
        return None
    key = keys[0]
    if key in d:
        return recursive_get(d[key], keys[1:])
    else:
        return None


def transform_to_emoncms(aira_enriched_state, export_rules):
    emoncms_format = {}
    for dest, source in export_rules.items():
        get_result = recursive_get(aira_enriched_state, source.split('/'))
        if get_result is not None:
            if type(get_result) == bool:
                # convert bool to int for EmonCMS
                emoncms_format[dest] = int(get_result)
            elif type(get_result) == float or type(get_result) == int:
                # only send numeric values
                emoncms_format[dest] = get_result
            else:
                logger.warning(f"Transformation: Skipping non-numeric value {get_result} for {dest} from source path {source}")
        else:
            logger.warning(f"Transformation: Failed to get value for {dest} from source path {source}")
    return emoncms_format


def upload_to_emoncms(aira_enriched_state, destination, export_rules):
    emoncms_data = transform_to_emoncms(aira_enriched_state, export_rules)
    emoncms_json = json.dumps(emoncms_data)
 
    post_data = {
        'node': destination['group'],
        'data': emoncms_json,
        'apikey': destination['api_key']
    }
    
    logger.debug(f'Posting to EmonCMS URL: {destination['url']} Data: {post_data}')
    try:
        x = requests.post(destination['url'], data=post_data, timeout=destination.get('timeout', 5))

        logger.debug(f'EmonCMS response code: {x.status_code} Text: {x.text}')
        if x.status_code != 200:
            raise Exception(f"Failed to post to EmonCMS - Response code: {x.status_code} Text: {x.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to post to EmonCMS - Exception: {e}")


def calc_heatpump_heat(deltaT, flowRate):
    heat = deltaT * 4184 * flowRate / 60 # Watts
    # avoid negative spikes
    if heat < 0:
        heat = 0
    return heat


def enrich_state(original_state, dhw_target_temp):
    global heatpump_hold_running

    enriched_state = original_state.copy()

    deltaT = original_state['system_check_state']['sensor_values']['outdoor_unit_supply_temperature'] - original_state['system_check_state']['sensor_values']['outdoor_unit_return_temperature']
    flowRate = original_state['system_check_state']['sensor_values']['flow_meter1']

    enriched_state['calculated_values'] = {}
    enriched_state['calculated_values']['heating_power'] = calc_heatpump_heat(deltaT, flowRate)

    # In theory the immmersion heater can also do central heating but unlikely
    enriched_state['calculated_values']['immersion_elec'] = 0
    if original_state['system_check_state']['inline_heater_status']['is_active']:
        enriched_state['calculated_values']['immersion_elec'] = original_state['system_check_state']['energy_calculation']['current_electrical_power_w']
        enriched_state['calculated_values']['heating_power'] = original_state['system_check_state']['energy_calculation']['current_electrical_power_w']

    heatpump_dhw = 0
    heatpump_ch = 0
    # Catch-all to see if heatpump is running for DHW or CH
    # If this fails, might resort to using flow rate > 0
    if original_state['system_check_state']['megmet_status']['requested_state'] or original_state['system_check_state']['megmet_status']['current_operation_mode'] or enriched_state['calculated_values']['immersion_elec']:
        if original_state['system_check_state']['valve_status']['dhw_heating_cooling_valve'] == 'POSITION_DHW':
            heatpump_dhw = 1
        else:
            heatpump_ch = 1
    enriched_state['calculated_values']['heatpump_dhw'] = heatpump_dhw
    enriched_state['calculated_values']['heatpump_ch'] = heatpump_ch
    
    # Simple hold counter to avoid spikes when heatpump stops by P0 is running
    if heatpump_dhw or heatpump_ch:
        heatpump_hold_running = 10
    else:
        heatpump_hold_running -= 1
        if heatpump_hold_running < 0:
            heatpump_hold_running = 0

    # If heatpump not running for 10 scan intervals, zero heating power
    if not heatpump_hold_running:
        enriched_state['calculated_values']['heating_power'] = 0

    # Too lazy to pull this from different BLE call, so just use configured value
    enriched_state['calculated_values']['dhw_target_temperature'] = dhw_target_temp

    return enriched_state


def load_config():
    with open(CONFIG_FILEPATH, 'r') as f:
        config = yaml.safe_load(f)
        return config
    
    logger.critical("Failed to load configuration file")
    exit(1)


def main():
    # Initialize the library
    aira = AiraHome()

    # Difficult to set log level of pyairahome - here appears to mostly work
    logging.getLogger('AiraHome').setLevel(LOGLEVEL)
    logging.getLogger('pyairahome').setLevel(LOGLEVEL)

    config = load_config()
    
    # Lazy additional functionality to scan for AIRA devices
    if config['settings']['aira_uuid'] == 'SCAN':
        logger.info("SCAN found in aira_uuid - performing scan and exiting")
        devices = aira.ble.discover(timeout=5)
        logger.info(devices)
        exit(0)

    logger.info(f"Connecting to AIRA device with UUID: {config['settings']['aira_uuid']}")
    connected = aira.ble.connect_uuid(config['settings']['aira_uuid'])
    
    if connected:
        logger.info("Connected: Entering upload loop")
        bad_tries = 0
        while True:
            start_scan = time.time()
            try:
                aira_state = aira.ble.get_system_check_state()
                # default=str to handle any non-serializable objects
                logger.debug(f"AIRA raw data: {json.dumps(aira_state, default=str)}")

                aira_enriched_state = enrich_state(aira_state, config['settings']['dhw_target_temp'])
                # default=str to handle any non-serializable objects
                logger.debug(f"AIRA enriched data: {json.dumps(aira_enriched_state, default=str)}")

                for dest in config['destination']:
                    try:
                        export_rules = config['export_rules'][dest['export_rule']]
                        upload_to_emoncms(aira_enriched_state, dest, export_rules)
                    except Exception as e:
                        logger.error(f"Failed to upload to EmonCMS destination {dest['url']} with exception: {e}")

                bad_tries = 0

            except BLEConnectionError as e:
                bad_tries += 1
                logger.warning(f"Exception {e} occurred - count of bad tries: {bad_tries}")
                if bad_tries > config['settings']['retries_before_restart']:
                    logger.critical("Too many failures - exiting")
                    exit(1)

                # this means there is a connection error, meaning aira is probably disconnected
                time.sleep(5) # wait some time
                aira.ble.connect() # reconnect

            except Exception as e:
                bad_tries += 1
                logger.warning(f"Exception {e} occurred - count of bad tries: {bad_tries}")
                if bad_tries > config['settings']['retries_before_restart']:
                    logger.critical("Too many failures - exiting")
                    exit(1)

            # wait until next scan, accounting for time taken to process
            required_wait = config['settings']['scan_interval'] - (time.time() - start_scan)
            if required_wait < 0:
                required_wait = 0
                logger.warning("Processing took longer than scan interval")
            logger.debug(f"Waiting {required_wait} seconds until next scan")
            time.sleep(required_wait)
    else:
        logger.critical("Failed to connect to Aira device - set SCAN as aira_uuid to scan for devices")


if __name__ == '__main__':
    main()

