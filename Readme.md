# pk5001z
custom component to retrieve data from a Zytel pk5001z DSL modem

### Getting started

* Add sensor.py, __init__.py and manifest.json to the Home Assistant config\custom_components\pk5001z directory

#### Home Assistant Example

```
configuration.yaml

sensor:
  - platform: pk5001z
    host: <Hostname/IP address of DSL modem>
    port: 80
    username: PORTAL_LOGIN
    password: PORTAL_PASSWORD
    scan_interval: 300
```

```
Creates the following sensors in Home Assistant

sensor.pk5001z_download
sensor.pk5001z_dsl_status
sensor.pk5001z_internet_status
sensor.pk5001z_ipv4_link_uptime
sensor.pk5001z_modem_ip
sensor.pk5001z_remote_ip
sensor.pk5001z_upload
```
