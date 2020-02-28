### Sub domains for application servers
- InfluxDB: https://flux.**** (port 8086)
- PostgreSQL: db.**** (port 6000)
- PgAdmin: https://pg.**** (port 5555)
- MQTT Broker: https://mqtt.**** (port 1882)
- Grafana: https://graf.**** (port 3000)
- Node Red: https://red.**** (port 1880) 

### Docker launches
All 3 application servers above are launched with Docker in detached mode with the `-d` tag
```bash
docker run -p 1880:1880 -d --name node_red_server nodered/node-red
docker run -p 8086:8086 -d --name influx_server influxdb
docker run -p 3000:3000 -d --name grafana_server grafana/grafana
docker run -it -p 1883:1883 -p 9001:9001 -d --name mqtt_broker -v mqtt:/mosquitto/data eclipse-mosquitto
```
To reattach to the container's terminal to see logs use the command
```bash
docker attach <container_name>
```
To access the container with a bash shell use the command
```bash
docker exec -it <container_name> bash
```
The default authentication for **grafana** is `admin` for both username and password. After first login we will be requested to change the passsword. To change the default admin password when launching the container, set the corresponding environment variable:
```bash
docker run -p 3000:3000 -d --name grafana_server -e "GF_SECURITY_ADMIN_PASSWORD=secret" grafana/grafana
```
For `grafana`, all default configurations are stored inside the container under `conf/defaults.ini` (which can be viewed if accessing the container with the bash shell).
To access the InfluxDB database(s) using the `influx` client: 
```bash
docker exec -it <container_name> influx
```
With this we can write InfluxDb or SQL queries like:
```bash
create database em_test
use em_test
```
To exit the bash shell, type `exit`.
In order to maintain the data of the DB, add a volume mountpoint to the docker container when launching the container:
```bash
docker run -p 8086:8086 -d --name influx_server -v influxdb:/var/lib/influxdb influxdb
```
The same can be done for `grafana` server with the tag `-v grafana:/var/lib/grafana`. 

### Additionals
#### To add authentication to MQTT broker:
- Copy the `mosquitto.conf`config file from the running MQTT Broker container using the following commands
```bash
docker exec -it mqtt_broker bin/ash                         # access the container with a terminal
cp /mosquitto/config/mosquitto.conf /mosquitto/data/        # copy the config file to the persistent data volume of Docker
exit                                                        # exit the terminal
```
-  Create a new `mqtt_config` folder containing an `auth.txt` authentication file with any set of username and password separated by a colon, each set in one line. For example:
```
admin:admin_password
user:user_password
```
-  Copy the `mosquitto.conf` config file from the Docker persistent data volume to this new folder
```bash
cp /var/lib/docker/volumes/mqtt/_data/mosquitto.conf .
```
-  Generate hash for the password(s) in the `auth.txt` file:
```bash
mosquitto_passwd -U auth.txt
```
- In the `mosquitto.conf` config file, set `allow_anonymous` to `false` and `password_file` to `/mosquitto/config/auth.txt`.
For more info, check [this tutorial](http://www.steves-internet-guide.com/mqtt-username-password-example/)
- Stop and remove the currently running MQTT Broker Docker container
```bash
docker stop mwtt_broker
docker rm mqtt_broker
```
- In the current folder containing the `mqtt_config` folder, run Docker command again to launch the MQTT broker container with authentications
```
docker run -it -p 1883:1883 -p 9001:9001 -d --name mqtt_broker -v mqtt:/mosquitto/data -v ${PWD}/mqtt_config:/mosquitto/config eclipse-mosquitto
```
#### To install World Map Panel plugin in grafana
- Access the container with a bash shell
```bash
docker exec -it grafana_server bash
```
   - Then use the `grafana-client` to install the plugin:
```bash
grafana-cli plugins install grafana-worldmap-panel
```
   - Restart the server
```bash
grafana-server restart
```
   - Exit the bash shell
```bash
exit
```
   - Restart the Docker container
```bash
docker stop grafana_server
docker start grafana_server
```
Now when we log in to `grafana` again, **World Map** will appear in the **Installed Panels** tab