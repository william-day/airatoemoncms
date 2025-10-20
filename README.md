## Requirements

This has been tested on

* Raspberry Pi 4 Model B
* Ubuntu 24.04

EMONCMS instance is required, this can either be hosted locally (free) or https://emoncms.org/ (paid).

## Usage

### Bluetooth must be installed/enabled

By default Ubuntu Server 24.04 does not have Bluetooth installed. Install and enable as follows.

```bash
sudo apt intall bluez
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

### Edit configuration

Edit docker-compose.yml and edit/populate the following

* AIRA_UUID
* AIRA_DHW_TARGET_TEMP
* EMONCMS_URL (only if using local server)
* EMONCMS_APIKEY (this is the read/write API key)

### Build and run 

```bash
sudo docker-compose up --build -d
```