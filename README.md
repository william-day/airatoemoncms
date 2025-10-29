## Description

This is a lightweight application which uses [pyairahome libary](https://github.com/Invy55/pyairahome) to pull Aira heatpump performance data via BLE and export to one or more instances of Emoncms.

Each instances may have different mappings for attributes, which can be useful when one has a local and cloud running instances.


## Requirements

This has been **only** been tested on

- Raspberry Pi 4 Model B
- Ubuntu 24.04

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

- dhw_target_temp
- aira_uuid
- Emoncms api_key

One can change the attribute filter for each destination to export additional fields. Useful filters are

- minimal
- minimal_plus_buffer
- minimal_plus_buffer_and_energy_balance
- minimal_plus_energy_balance
- verbose

### Aira UUID

If you do not know your Aira UUID, set `SCAN` as `aira_uuid` and the results will be written to `logs/airatoemoncms.log`


### Build and run 

```bash
sudo docker-compose up --build -d
```

Newer versions would be `docker compose` but example assumes default package in Ubuntu 24.04.

### Updates

If configuration is changed, either docker-compose.yml or airatoemoncms.yml, load new state with.


```bash
 sudo docker-compose down
sudo docker-compose up -d
```

If app is updated, rebuild the container as follows.

```bash
 sudo docker-compose down
 sudo docker-compose up --build --remove-orphans -d
```

### Logs

Logs are written to `logs/airatoemoncms.log`

## Disclaimer

### This app uses pyairahome library with the following disclaimer

**PyAiraHome** is an independent, open-source software library developed for interacting with Aira Home heat pumps via their app gRPC APIs and Bluetooth Low Energy protocols. This project is **not affiliated with, endorsed by, sponsored by, or associated with** Aira Home or any of its subsidiaries, affiliates, or partners.

#### Important Legal Notice

- 🔒 This project is **not an official product** of Aira Home
- ⚖️ Use of this library does **not imply any compatibility, support, or approval** from Aira Home
- 🏷️ All trademarks, service marks, and company names mentioned herein are the **property of their respective owners**
- ⚠️ **Use of this library is at your own risk** - I'm not responsible for any damages, malfunctions, warranty voids, or issues arising from its use
- 🛡️ This software is provided **"AS IS"** without warranty of any kind, express or implied
- 🔍 No proprietary code, trade secrets, or copyrighted materials from Aira Home have been used in the development of this library.

**By using this library, you acknowledge that you understand and accept these terms and any associated risks.**

### This app

In addition to the disclaimer above.

- This App is **not an official product** of Aira Home
- Use of this App does **not imply any compatibility, support, or approval** from Aira Home
- All trademarks, service marks, and company names mentioned herein are the **property of their respective owners**
- **Use of this App is at your own risk** - I'm not responsible for any damages, malfunctions, warranty voids, or issues arising from its use
- This software is provided **"AS IS"** without warranty of any kind, express or implied
- No proprietary code, trade secrets, or copyrighted materials from Aira Home have been used in the development of this App.
