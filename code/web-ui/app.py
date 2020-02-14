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
import json


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

    def __init__(self, user, email, password):
        self.user       = user
        self.password   = password
        self.email      = email


class Bin(db.Model):
    __tablename__ = 'bin'
    bin_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    type_id = db.Column(db.BigInteger)
    device_id = db.Column(db.BigInteger) 
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    address = db.Column(db.JSON())
    
    def __init__(self, bin_id, type_id, device_id, latitude, longitude):
        self.bin_id = bin_id
        self.type_id       = type_id
        self.device_id   = device_id
        self.latitude      = latitude
        self.longitude = longitude
    def save(self):
        # inject self into db session    
        db.session.add ( self )
        # commit change and save the object
        db.session.commit( )
    
class BinType(db.Model):
    __tablename__ = 'bin_type'
    type_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    art = db.Column(db.String(20))
    anzahl_behalter = db.Column(db.SmallInteger)
    abfuhr_tag = db.Column(db.String(10))
    wochen_g_ug = db.Column(db.Boolean) 
    zeit_bedarf = db.Column(db.Float)

    def __init__(self, type_id, art, anzahl_behalter, abfuhr_tag, wochen_g_ug, zeit_bedarf):
        self.type_id   = type_id
        self.art   = art
        self.anzahl_behalter  = anzahl_behalter
        self.abfuhr_tag = abfuhr_tag
        self.wochen_g_ug = wochen_g_ug
        self.zeit_bedarf = zeit_bedarf
    def save(self):
        # inject self into db session    
        db.session.add ( self )
        # commit change and save the object
        db.session.commit( )

class Device(db.Model):
    __tablename__ = 'device'
    device_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    device_ttn_id = db.Column(db.String(50), unique = True)
    sensor_id = db.Column(db.BigInteger)
    description = db.Column(db.String(100))

    def __init__(self, device_id, device_ttn_id, sensor_id, description):
        self.device_id   = device_id
        self.device_ttn_id      = device_ttn_id
        self.sensor_id = sensor_id
        self.description = description
    def save(self):
        # inject self into db session    
        db.session.add ( self )
        # commit change and save the object
        db.session.commit( )

class Sensor(db.Model):
    __tablename__ = 'sensor'
    sensor_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    name = db.Column(db.String(20))
    meas_type = db.Column(db.String(50))
    meas_unit = db.Column(db.String(10))
    description = db.Column(db.String(100))

    def __init__(self, sensor_id, name, meas_type, meas_unit, description):
        self.sensor_id       = sensor_id
        self.name   = name
        self.meas_type      = meas_type
        self.meas_unit = meas_unit
        self.description = description
    def save(self):
        # inject self into db session    
        db.session.add ( self )
        # commit change and save the object
        db.session.commit( )

class Gateway(db.Model):
    __tablename__ = 'ttn_gateway'
    gw_id = db.Column(db.BigInteger, primary_key = True, nullable = False)
    gw_ttn_id = db.Column(db.String(50), unique = True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    altitude = db.Column(db.Float)

db.create_all()   #create all tables if not exists


def get_fill_percent(dist_from_top):
    fill_level = bin_max_height - dist_from_top
    if 0 <= 100*fill_level/bin_max_height <= 25:
        return 25
    elif 25 < 100*fill_level/bin_max_height <= 50:
        return 50
    elif 50 < 100*fill_level/bin_max_height <= 75:
        return 75
    elif 75 < 100*fill_level/bin_max_height <= 100:
        return 100


""" 
BEGIN OF INDEX ROUTING >>>
"""
@app.route('/', defaults={'path': 'index.html'}, methods=['GET', 'POST'])
def index(path):
    if current_user.is_authenticated:
        geojson_data = []
        all_bin_types = BinType.query.all()
        meas_name = "sensor_data"
        res_set = influx_client.query("SELECT * from {} GROUP BY * ORDER BY DESC".format(meas_name))
        num_filled_bins = 0
        avg_fill_level = 0
        valid_bin_count = 0
        for bin_type in all_bin_types:
            bin_data = Bin.query.filter_by(type_id = bin_type.type_id).all()
            for bin in bin_data:
                if bin.latitude and bin.longitude is not None:
                    if bin.address:
                        loc = bin.address
                    else:
                        try:
                            loc = geolocator.reverse("{}, {}".format(bin.latitude, bin.longitude)).raw["address"]
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
                        try:
                            sensor_dist = list(res_set.get_points(tags={'device_id': device_ttn_id}))[0][field_key]
                            print(sensor_dist)
                            fill_level = get_fill_percent(sensor_dist)
                        except:
                            fill_level = 0
                        if fill_level >= 75:
                            num_filled_bins = num_filled_bins + 1
                        print("bin {0}, fill level: {1}".format(bin.bin_id, fill_level))
                    else:
                        fill_level = ""
                    if fill_level:
                        avg_fill_level = avg_fill_level + fill_level
                        valid_bin_count = valid_bin_count + 1
                    try:
                        house_number = loc["house_number"]
                    except:
                        house_number = ""
                    try:
                        road = loc["road"] + ","
                    except:
                        road = ""
                    try:
                        neighbourhood = loc["neighbourhood"] + ","
                    except:
                        neighbourhood = ""
                    try:
                        suburb = loc["suburb"]   
                    except:
                        suburb = ""
                    geojson_data.append({
                        "type": "Feature",
                        "properties": {
                            "name": bin.bin_id,
                            "bin_type": bin_type.art,
                            "fill_level": fill_level,
                            "address": loc,
                            "popupContent": "{0} {1} {2} {3}".format(house_number, road, neighbourhood, suburb)
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [bin.longitude, bin.latitude]
                        }
                    })
        return render_template('default.html', active_page='index',
                                    content=render_template('index.html',
                                    geojson_data=geojson_data,
                                    all_bin_types=all_bin_types,
                                    num_filled_bins=num_filled_bins,
                                    avg_fill_level=avg_fill_level/valid_bin_count))
    else:
        flash("Please register or log in", "danger")
        return render_template('default.html',
                                content=render_template('login.html'))
                                
""" 
END OF INDEX ROUTING <<<
""" 


""" 
BEGIN OF BIN MANAGER >>>
"""
@app.route('/bins.html', methods=['GET', 'POST'])
def bins_manager():
    all_bin_types = BinType.query.all()
    all_bins = []
    meas_name = "sensor_data"
    res_set = influx_client.query("SELECT * from {} GROUP BY * ORDER BY DESC".format(meas_name))
    sensor = ""
    for bin_type in all_bin_types:
        bin_data = Bin.query.filter_by(type_id = bin_type.type_id).order_by(Bin.bin_id.asc()).all()
        for bin in bin_data[:30]:
            fill_level = 0
            if bin.latitude and bin.longitude is not None:
                if bin.address:
                    loc = bin.address
                else:
                    loc = 'Unknown'
                device = Device.query.filter_by(device_id=bin.device_id).first()
                if device:
                    sensor = Sensor.query.filter_by(sensor_id=device.sensor_id).first()
                    if sensor:
                        try:
                            sensor_dist = list(res_set.get_points(tags={'device_id': device.device_ttn_id}))[0][field_key]
                            fill_level = get_fill_percent(sensor_dist)
                        except:
                            fill_level = 0
                all_bins.append({
                            "bin_id": bin.bin_id,
                            "bin_type": bin_type.art,
                            "fill_level": fill_level if fill_level > 0 else "NA",
                            "device_name": device.device_ttn_id if device else "None",
                            "address" : loc,
                            "coordinates": [bin.latitude, bin.longitude],
                            "sensor": sensor.name if sensor else "None"
                        })
    if request.method == "POST":
        print(request.form)
        if request.form["btn"] == "update_bin":
            try:
                bin_id = request.form["selected_bin"]
                bin_type = request.form["bin_type"]
                device = request.form["device"]
                sensor = request.form["sensor"]
                loc = request.form["location"].split(",")
                try:
                    if device == "None":
                        device_id = -1
                    else:
                        device_id = Device.query.filter_by(device_ttn_id=device).first()
                        if sensor == "None":
                            sensor_id = -1
                        else:
                            sensor_id = Sensor.query.filter_by(name=sensor).first().sensor_id
                            device_id.sensor_id = sensor_id
                    try:
                        bin = Bin.query.filter_by(bin_id=bin_id).first()
                        db.session.commit()
                    except Exception as e:
                        print("Cannot update bin {} in database. Error: ".format(bin_id), e)
                        flash("Unable to update bin", "danger")
                        return redirect("/bins.html")
                    else:
                        print("Cannot find bin {} in database. Creating device...".format(bin_id))
                        try:
                            bin_id = request.form["bin_id"]
                            bin = Bin(bin_id, bin_type, device_id, loc[0], loc[1])
                            bin.save()
                        except Exception as e:
                            print("Cannot create bin {}. Error: ".format(bin_id), e)
                            flash("Unable to create bin", "danger")
                            return redirect("/bins.html")
                except Exception as e:
                    print("Cannot find device {} in database. Details:".format(device), e)
                    flash("Unable to update bin", "danger")
                    return redirect("/bins.html")
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to update bin", "danger")
                return redirect("/bins.html")
            flash("Successfully bins bin", "success")
            return redirect("/bins.html")
        elif request.form["btn"] == "delete_bin":
            try:
                bin_id = request.form["delete_bin"]
                try:
                    bin = Bin.query.filter_by(bin_id=bin_id).first()
                    if bin:
                        db.session.delete(bin)
                        db.session.commit()
                        flash("Successfully deleted bin {}".format(bin_id), "success")
                        return redirect("/bins.html")
                except Exception as e:
                    print("Cannot find bin {} in database. Details: ".format(bin_id),e)
                    flash("Unable to delete bin", "danger")
                    return redirect("/bins.html")
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to delete bin", "danger")
                return redirect("/bins.html")
    return render_template('default.html', active_page='bins',
                                    content=render_template('bins.html',
                                    all_bins=all_bins,
                                    all_bin_types=all_bin_types,
                                    all_devices=Device.query.all(),
                                    all_sensors=Sensor.query.all()))
                                
""" 
END OF BIN MANAGER <<<
""" 

""" 
BEGIN OF DEVICE MANAGER <<<
""" 

@app.route('/devices.html', methods=['GET', 'POST'])
def device_manager():
    all_devices = Device.query.order_by(Device.device_id.asc()).all()
    device_data = []
    
    for device in all_devices:
        sensor = Sensor.query.filter_by(sensor_id=device.sensor_id).first()
        device_data.append({
            "dev_id": device.device_id,
            "ttn_id": device.device_ttn_id,
            "sensor": sensor.name if sensor else "None",
            "desc": device.description
        })
    if request.method == "POST":
        if request.form["btn"] == "update_device":
            try:
                dev_id = request.form["selected_dev"]
                sensor = request.form["sensor"]
                desc = request.form["desc"]
                try:
                    if sensor == "None":
                        sensor_id = -1
                    else:
                        sensor_id = Sensor.query.filter_by(name=sensor).first().sensor_id
                    device = Device.query.filter_by(device_id=dev_id).first()
                    if device:
                        device.sensor_id = sensor_id
                        device.description = desc
                        try:
                            db.session.commit()
                        except Exception as e:
                            print("Cannot update device {} in database. Error: ".format(dev_id), e)
                            flash("Unable to update device", "danger")
                            return redirect("/devices.html")
                    else:
                        print("Cannot find device {} in database. Creating device...".format(dev_id))
                        try:
                            ttn_id = request.form["ttn_id"]
                            device = Device(dev_id, ttn_id, sensor_id, desc)
                            device.save()
                        except Exception as e:
                            print("Cannot create device {}. Error: ".format(dev_id), e)
                            flash("Unable to create device", "danger")
                            return redirect("/devices.html")
                except Exception as e:
                    print("Cannot find sensor {} in database. Details:".format(sensor), e)
                    flash("Unable to update device", "danger")
                    return redirect("/devices.html")
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to update device", "danger")
                return redirect("/devices.html")
            flash("Successfully updated device", "success")
            return redirect("/devices.html")
        elif request.form["btn"] == "delete_device":
            try:
                dev_id = request.form["delete_dev"]
                try:
                    device = Device.query.filter_by(device_id=dev_id).first()
                    if device:
                        db.session.delete(device)
                        db.session.commit()
                        flash("Successfully deleted device {}".format(dev_id), "success")
                        return redirect("/devices.html")
                except Exception as e:
                    print("Cannot find device {} in database. Details: ".format(dev_id),e)
                    flash("Unable to delete device", "danger")
                    return redirect("/devices.html")
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to delete device", "danger")
                return redirect("/devices.html")
    return render_template('default.html', active_page='devices',
                                    content=render_template('devices.html',
                                    device_data=device_data,
                                    all_sensors=Sensor.query.all()))

""" 
END OF DEVICE MANAGER <<<
""" 

""" 
BEGIN OF SENSOR MANAGER <<<
""" 

@app.route('/sensors.html', methods=['GET', 'POST'])
def sensor_manager():
    all_sensors = Sensor.query.order_by(Sensor.sensor_id.asc()).all()
    sensor_data = []
    
    for sensor in all_sensors:
        sensor_data.append({
            "sensor_id": sensor.sensor_id,
            "name": sensor.name,
            "meas_type": sensor.meas_type,
            "meas_unit": sensor.meas_unit,
            "desc": sensor.description
        })
    if request.method == "POST":
        if request.form["btn"] == "update_sensor":
            try:
                sensor_id = request.form["sensor_id"]
                name = request.form["name"]
                meas_type = request.form["meas_type"]
                meas_unit = request.form["meas_unit"]
                desc = request.form["desc"]
                
                sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
                if sensor:
                    sensor.name = name
                    sensor.meas_type = meas_type
                    sensor.meas_unit = meas_unit
                    sensor.description = desc
                    try:
                        db.session.commit()
                    except Exception as e:
                        print("Cannot update sensor {} in database. Error: ".format(sensor_id), e)
                        flash("Unable to update sensor", "danger")
                        return redirect("/sensors.html")
                else:
                    print("Cannot find sensor {} in database. Creating sensor...".format(sensor_id))
                    try:
                        sensor = Sensor(sensor_id, name, meas_type, meas_unit, desc)
                        sensor.save()
                    except Exception as e:
                        print("Cannot create sensor {}. Error: ".format(sensor_id), e)
                        flash("Unable to create sensor", "danger")
                        return redirect("/sensors.html")
                
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to update sensor", "danger")
                return redirect("/sensors.html")
            flash("Successfully updated sensor", "success")
            return redirect("/sensors.html")
        elif request.form["btn"] == "delete_sensor":
            try:
                sensor_id = request.form["delete_sensor"]
                try:
                    sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
                    if sensor:
                        db.session.delete(sensor)
                        db.session.commit()
                        flash("Successfully deleted sensor {}".format(sensor_id), "success")
                        return redirect("/sensors.html")
                except Exception as e:
                    print("Cannot find sensor {} in database. Details: ".format(sensor_id),e)
                    flash("Unable to delete sensor", "danger")
                    return redirect("/sensors.html")
            except Exception as e:
                print("Error parsing POST request: ",e)
                flash("Unable to delete sensor", "danger")
                return redirect("/sensors.html")
    return render_template('default.html', active_page='sensors',
                                    content=render_template('sensors.html',
                                    sensor_data=sensor_data))

""" 
END OF SENSOR MANAGER <<<
""" 


""" 
BEGIN OF REGISTER/LOGIN/LOGOUT ROUTING >>>
"""
# register user
@app.route('/register.html', methods=['GET', 'POST'])
def register():

    msg = None

    if request.method == 'GET': 

        return render_template('default.html',
                                content=render_template('register.html'))

    # check if both http method is POST and form is valid on submit
    else:
    
        # assign form data to variables
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password) 
        email = request.form["email"]

        # filter User out of database through username
        user = User.query.filter_by(user=username).first()

        # filter User out of database through username
        user_by_email = User.query.filter_by(email=email).first()

        if user or user_by_email:
            if user:
                msg = 'Error: User {} already exists!'.format(username)
            elif user_by_email:
                 msg = 'Error: Email {} already exists!'.format(email)
            flash(msg, "danger")
        
        else:         
            user = User(username, email, pw_hash)
            user.save()
            msg = 'User created, please login' 
            flash(msg, "success")
            return render_template('default.html',
                                content=render_template('login.html'))

    return render_template('default.html',
                                content=render_template('register.html'))



# Login routing 
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        try:
            # assign form data to variables
            username = request.form["username"]
            password = request.form["password"]
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
        except:
            return render_template('default.html',
                                content=render_template('login.html'))
    return render_template('default.html',
                                content=render_template('login.html'))

# provide login manager with load_user callback
@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    if current_user.is_authenticated:
        try:
            return render_template('default.html',
                                    content=render_template(path))
        except:
            return render_template('default.html',
                                    content=render_template('404.html'))
    else:
        flash("Please register or log in", "danger")
        return render_template('default.html',
                                content=render_template('login.html'))

""" 
END OF OTHER ROUTING <<<
"""


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True,port=5020)