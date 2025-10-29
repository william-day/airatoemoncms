## Description

This is a lightweight application which used pyairahome libary to pull Aira heatpump performance data via BLE and export to one or more instances of Emoncms.

Each instances may have different mappings for attributes, which can be useful when one has a local and cloud running instances.


## Requirements

This has been **only** been tested on

* Raspberry Pi 4 Model B
* Ubuntu 24.04

Emoncms instance is required, this can either be hosted locally (free) or https://emoncms.org/ (paid).

## Usage

### Bluetooth must be installed/enabled

By default Ubuntu Server 24.04 does not have Bluetooth installed. Install and enable as follows.

```bash
sudo apt intall bluez
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

### Edit configuration

Copy example config to `config/airatoemoncms.yml`

```bash
cp config/airatoemoncms.yml.example config/airatoemoncms.yml
```

Edit `config/airatoemoncms.yml`

The minimal configuration which must be changed is

* dhw_target_temp
* aira_uuid
* Emoncms api_key

One can change the attribute filter for each destination to export additional fields. Useful filters are

* minimal
* minimal_plus_buffer
* minimal_plus_buffer_and_energy_balance
* minimal_plus_energy_balance
* verbose

### Aira UUID

If you do not know your Aira UUID, set `SCAN` as `aira_uuid` and the results will be written to `logs/airatoemoncms.log`


### Build and run 

```bash
sudo docker-compose up --build -d
```

Newer versions would be `docker compose` but example assumes default package in Ubuntu 24.04.

## Disclaimer

