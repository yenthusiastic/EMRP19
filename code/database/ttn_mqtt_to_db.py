"""
Python script to subscribe to TTN MQTT Broker to fetch sensor data and save to InfluxDB
TTN MQTT API Reference: https://www.thethingsnetwork.org/docs/applications/mqtt/api.html
Original version: https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/code/DatabaseScripts/mqtt_connect.py
Modified by Thu Nguyen 13.02.2020
""" 
# Import required libraries
## Paho Library for MQTT communication
import paho.mqtt.client as mqtt
## Json library to handle jason file from ttn
import json
## InfluxDB client library
from influxdb import InfluxDBClient
## PostgreSQL client library
import psycopg2


# Database authentication
## InfluxDB
influx_host = "*****"
influx_port = "****"
influx_user = "****"
influx_password = "****"
influx_dbname = "****"

## PostgreSQL
psql_host='****'
psql_port=5555
psql_dbname='****'
psql_user='****'
psql_password='****'


# Initialize database connection
## InfluxDB
try:
    print('Connecting to the InfluxDB database...')
    influx_client = InfluxDBClient(influx_host, influx_port, influx_user, influx_password, influx_dbname)
    influx_client.switch_database(influx_dbname)
    print("Successfully connected to InfluxDB")
except Exception as e:
    print("Failed to connect to InfluxDB database", e)

## PostgreSQL
try:        
    # connect to the PostgreSQL server
    print('Connecting to the PostgreSQL database...')
    psql_conn = psycopg2.connect(host=psql_host, port=psql_port, user=psql_user, password=psql_password, database=psql_dbname)
    print("Successfully connected to DB")
except (Exception, psycopg2.DatabaseError) as e:
    print("Faied to connect to PostgreSQL database...")

    
# Application authentication, can be found under APPLICATION OVERVIEW in the TTN console 
## Application EUI & ID
APPEUI = "70B3D57ED00271EA"
APPID  = "wastebin_19"
## APPLICATION ACCESS KEY
PSW    = 'ttn-account-v2.DLYXYF8PY_Py6SaidkOqBo_SDokxXnwSl5khQPM2PVs'


# Key of dictionary object from which to read the sensor data from
payload_key = "digital_out_1"
device_key = "digital_out_2"

#Call back functions

# gives connection message
def on_connect(mqttc, mosq, obj,rc):
    #simply prints the status of connection. For example "0" for connection established
    print("Connected with result code:"+str(rc)) 
    # subscribe for all devices of user
    mqttc.subscribe('+/devices/+/up')
    
    

# gives message from device
def on_message(mqttc,obj,msg):
    try:

        #to simply print our topic
        print("topic is ", msg.topic)
        
        #here the original message from TTN that is in json format is decoded into dictionary format
        x = json.loads(msg.payload.decode('utf-8'))
        #print(x)

        #Extraction of all these values from the original message as they all are dictionary data type
        payload_raw = (x["payload_raw"])       
        port_number = (x["port"])
        hardware_serial_number = (x["hardware_serial"])
        device = (x["dev_id"])
        counter = (x["counter"])
        application_id = (x["app_id"])
        airtime_value = (x["metadata"]["airtime"])
        
        payload_fields = x["payload_fields"]
        print("payload: ", payload_fields)

        #measurement_values = (str(list(payload_fields.keys())))
        datetime = x["metadata"]["time"]

        gateways = x["metadata"]["gateways"]
        
        frequency_value = (x["metadata"]["frequency"])
        data_rate_value = (x["metadata"]["data_rate"])
        modulation_value = (x["metadata"]["modulation"])
        coding_rate_value = (x["metadata"]["coding_rate"])
                        
        #this payload_fileds contain the main data which we are measuring . For example distance, temperature
        payload_fields = x["payload_fields"]

        #these if conditions is used when feeding data to sensor data table as we have currently three devices and to recognize device by hardcoded id
#         if device == "heltech_lora":
#               fetched_deviceId = 501
        
        # print for every gateway that has received the message and extract RSSI
        for gw in gateways:

            #inside metadata, we have gateways and inside gateways we have all these below values . they are in dictionary data type as well
            gateway_id = gw["gtw_id"]
            latitude = gw['latitude']
            longitude = gw['longitude']
            timestamp = gw['time']
            altitude = gw['altitude']
            
            # insert sensor measurement into InfluxDB table
            try:
                data = [{"measurement": "sensor_data", "time": timestamp, "fields": {"meas_value": payload_fields[payload_key]}, "tags": {"gateway_id": gateway_id, "device_id": device}}]
                influx_client.write_points(data)      
                print("Successfully inserted sensor data into InfluxDB")
            except Exception as e:
                print("Failed to insert record into InfluxDB table: ", e)

            # update last sensor measurement in PostgreSQL table
            try:
                sensor_val = payload_fields[payload_key]
                
                query = "SELECT device_id, latitude, longitude from public.bin INNER JOIN public.device ON (bin.device_id = device.device_id) WHERE device_ttn_id = '{}'".format(device)
                cur = psql_conn.cursor()
                cur.execute(query)
                psql_conn.commit()
                res = cur.fetchone()
                if res:
                    query = "SELECT * from public.last_fill_level WHERE device_id = {}".format(res[0])
                    cur.execute(query)
                    psql_conn.commit()
                    ret = cur.fetchone()
                    if ret:
                        query = """ UPDATE public."last_fill_level" SET meas_val = {0}, coordinates = POINT({1},{2}) WHERE device_id = {3}""".format(sensor_val, res[1], res[2], res[0])
                    else:
                        query = """ INSERT INTO public."last_fill_level"(device_id, meas_val, coordinates) VALUES ({0},{1},POINT({2},{3}))""".format(res[0], sensor_val, res[1], res[2])
                    print("Executing query...", query)
                    cur.execute(query)
                    psql_conn.commit()
                    print("Successfully inserted/updated sensor data in PostgreSQL table")
                else:
                    print("Failed to insert/update PostgreSQL table: Device {} not found".format(device))
            except Exception as e:
                print("Failed to insert/update PostgreSQL table: ", e)
                
            #insert gateway or update information into PostgreSQL table
#             try:
#                 query = "SELECT * FROM ttn_gateway WHERE gw_ttn_id = ''".format(gateway_id)
#                 cur = psql_conn.cursor()
#                 cur.execute(query)
#                 psql_conn.commit()
#                 res = cur.fetchone()
#                 if res:
#                     query = "UPDATE ttn_gateway SET latitude = {}, longitude = {}, altitude = {} WHERE gw_ttn_id = '{}'".format(latitude, longitude, altitude, gateway_id)
#                 else:
#                     query = "INSERT INTO ttn_gateway(latitude, longitude, altitude, gw_ttn_id) values ({}, {}, {}, '{}')".format(latitude, longitude, altitude, gateway_id)
#                 cur.execute(msg)
#                 psql_conn.commit()
#                 print("Successfully updated gateway data in PostgreSQL database")
#              #if any exception occurs during database communication
#             except Exception as e:
#                 print("Error executing query {}: Failed to update gateway data in PostgreSQL table: ".format(query), e)
            
            
    #if any exception occurs during message sending process from TTN
    except Exception as e:
        print("Failed to fetch data from TTN: ", e)
        pass


#creating object of mqtt client
mqttc= mqtt.Client()

# Assign event callbacks
mqttc.on_connect=on_connect
mqttc.on_message=on_message

#creating connection to the things network 
mqttc.username_pw_set(APPID, PSW)
mqttc.connect("eu.thethings.network",1883)


# and listen to server
run = True
while run:
    mqttc.loop()
