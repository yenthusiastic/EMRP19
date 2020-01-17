"""
Python script to insert the bin ID and corresponding location of all Paper bins in Moers given by ENNI in the paper_bins.csv file into the PostgreSQL database table named "bin"
Created by Thu Nguyen 17.01.2020
""" 
# PostgreSQL client library
import psycopg2
from datetime import datetime
import csv

# name of CSV file
csv_data = "paper_bins.csv"
bin_type = 1 #bin type is 1 for "Papierkorb"

# Database authentication
psql_host='****'
psql_port=9999
psql_dbname='****'
psql_user='****'
psql_password='****'

# Initialize database connection
try:        
    # connect to the PostgreSQL server
    print('Connecting to the PostgreSQL database...')
    psql_conn = psycopg2.connect(host=psql_host, port=psql_port, user=psql_user, password=psql_password, database=psql_dbname)
    print("Successfully connected to DB")
except (Exception, psycopg2.DatabaseError) as e:
    print("Faied to connect to PostgreSQL database...")


with open(csv_data, newline='') as csv_file:
    bin_data = csv.reader(csv_file, delimiter=',')
    for index, row in enumerate(bin_data):
        if index != 0:
            bin_id = row[0][11:]
            lat = row[1]
            lon = row[2]
            cursor = psql_conn.cursor()
            postgres_insert_query = """ INSERT INTO public."bin" (bin_id, longitude, latitude) VALUES (%s,%s,%s) RETURNING "bin_id" """
            record_to_insert = (bin_id, lon, lat)
            cursor.execute(postgres_insert_query, record_to_insert)
            fetched_bin_id = cursor.fetchone()[0]
            psql_conn.commit()
            print ("Record of bin ID {} successfully inserted into  table 'bin'".format(fetched_bin_id))