from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime
import os
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from flask_login import LoginManager
from flask_bcrypt     import Bcrypt
from geopy.geocoders import Nominatim
from influxdb import InfluxDBClient


geolocator = Nominatim(user_agent="EMRP19", timeout=10)

app = Flask(__name__)

base_dir = os.path.abspath(os.path.dirname(__file__))
print(base_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg2://arp_b:iota999@db.dev.iota.pw:6000/em_wastebin"
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}//db.db'.format(base_dir)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = "@W3o#92$uBDJX" 

bc = Bcrypt      (app) # flask-bcrypt
lm = LoginManager(   ) # flask-loginmanager
lm.init_app(app) # init the login manager

# Database authentication
## InfluxDB
influx_host = "flux.dev.iota.pw"
influx_port = "8086"
influx_user = "admin"
influx_password = "admin"
influx_dbname = "em_wastebin"

# Initialize database connection
## InfluxDB
try:
    print('Connecting to the InfluxDB database...')
    influx_client = InfluxDBClient(influx_host, influx_port, influx_user, influx_password, influx_dbname)
    influx_client.switch_database(influx_dbname)
    print("Successfully connected to InfluxDB")
except Exception as e:
    print("Failed to connect to InfluxDB database", e)
    

@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

data_dir = os.path.join(base_dir, "static/data")

bin_max_height = 71 #maximum height of the bin's fill level in centimeter

field_key = "meas_value" #name of data field for Influx database


db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id       = db.Column(db.BigInteger, primary_key=True)
    user     = db.Column(db.String(20),  unique = True)
    email    = db.Column(db.String(50), unique = True)
    password = db.Column(db.String(500))


class Bin(db.Model):
    __tablename__ = 'bin'
    bin_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    type_id = db.Column(db.BigInteger)
    device_id = db.Column(db.BigInteger) 
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.Text)
    
class BinType(db.Model):
    __tablename__ = 'bin_type'
    type_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    art = db.Column(db.String(20))
    anzahl_behalter = db.Column(db.SmallInteger)
    abfuhr_tag = db.Column(db.String(10))
    wochen_g_ug = db.Column(db.Boolean) 
    zeit_bedarf = db.Column(db.Float)

class Device(db.Model):
    __tablename__ = 'device'
    device_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    device_ttn_id = db.Column(db.String(50), unique = True)
    sensor_id = db.Column(db.BigInteger)
    description = db.Column(db.String(100))

class Sensor(db.Model):
    __tablename__ = 'sensor'
    sensor_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    name = db.Column(db.String(20))
    meas_type = db.Column(db.String(50))
    meas_unit = db.Column(db.String(10))
    description = db.Column(db.String(100))

class Gateway(db.Model):
    __tablename__ = 'ttn_gateway'
    gw_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    gw_ttn_id = db.Column(db.String(50), unique = True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float)

db.create_all()   #create all tables if not exists

def insert_user():
    user = User(user="emrp19", email="emrp@hsrw.org", password = generate_password_hash("emrp19"))
    db.session.add(user)
    db.session.commit()


#insert_user()


""" 
BEGIN OF INDEX ROUTING >>>
"""
@app.route('/', defaults={'path': 'index.html'}, methods=['GET', 'POST'])
def index(path):
    geojson_data = []
    all_bin_types = BinType.query.all()
    meas_name = "sensor_data"
    res_set = influx_client.query("SELECT * from {} GROUP BY * ORDER BY DESC".format(meas_name))
    for bin_type in all_bin_types:
        bin_data = Bin.query.filter_by(type_id = bin_type.type_id).all()
        for bin in bin_data:
            if bin.latitude and bin.longitude is not None:
                if bin.address:
                    loc = bin.address
                else:
                    try:
                        loc = '{}'.format(geolocator.reverse("{}, {}".format(bin.latitude, bin.longitude)).raw["address"])
                        this_bin = Bin.query.filter_by(bin_id=bin.bin_id).first()
                        this_bin.address = loc
                        db.session.commit()
                    except:
                        loc = 'Unknown'
                #print(loc)
                if bin.device_id:
                    #sensor_dist = 10
                    device_ttn_id = Device.query.filter_by(device_id=bin.device_id).first().device_ttn_id
                    #print(device_ttn_id)
                    sensor_dist = list(res_set.get_points(tags={'device_id': device_ttn_id}))[0][field_key]
                    print(sensor_dist)
                    fill_level = bin_max_height - sensor_dist
                    if 0 <= 100*fill_level/bin_max_height <= 25:
                        fill_level = 25
                    elif 25 < 100*fill_level/bin_max_height <= 50:
                        fill_level = 50
                    elif 50 < 100*fill_level/bin_max_height <= 75:
                        fill_level = 75
                    elif 75 < 100*fill_level/bin_max_height <= 100:
                        fill_level = 100
                    print("bin {0}, fill level: {1}".format(bin.bin_id, fill_level))
                else:
                    fill_level = ""
                geojson_data.append({
                    "type": "Feature",
                    "properties": {
                        "name": bin.bin_id,
                        "bin_type": bin_type.art,
                        "fill_level": fill_level,
                        "address": loc
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [bin.longitude, bin.latitude]
                    }
                })
    return render_template('default.html', active_page='index',
                                content=render_template('index.html',
                                geojson_data=geojson_data,
                                all_bin_types=all_bin_types))
                                
""" 
END OF INDEX ROUTING <<<
""" 



""" 
BEGIN OF LOGIN/LOGOUT ROUTING >>>
"""
# Login routing 
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        if request.form["btn"] == "login":
            # assign form data to variables
            username = request.form["user"]
            password = request.form["pwd"]
            # filter User out of database through username
            user = User.query.filter_by(user=username).first()
            if user:
                if check_password_hash(user.password, password):
                    login_user(user)
                    current_user.user = username
                    print("User {} logged in".format(username))
                    flash("Successfully logged in", "success")
                    return redirect('/')
                else:
                    flash("Username or password invalid Please try again.", "danger")
    return render_template('default.html',
                                content=render_template('login.html'))

# Logout routing 
@app.route('/logout')
def logout():
    print("User {} logged out".format(current_user.user))
    logout_user()
    flash("Successfully logged out", "success")
    return redirect('/')
    
""" 
END OF LOGIN/LOGOUT ROUTING <<<
"""

""" 
BEGIN OF BIN MANAGER ROUTING >>>
"""
@app.route('/bins')
def bin_manager():
    return redirect('/bin-manager.html')


""" 
END OF BIN MANAGER ROUTING <<<
"""



""" 
BEGIN OF OTHER ROUTING >>>
"""
@app.route('/<path>', methods=['GET', 'POST'])
def routing(path):
    try:
        return render_template('default.html',
                                content=render_template(path))
    except:
        return render_template('default.html',
                                content=render_template('404.html'))

""" 
END OF OTHER ROUTING <<<
"""


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True,port=5020)