**WARNING**: This readme is obsolete. To-be-updated.

This describes how to set up and run OpenAgua on a server, including configuration settings.

See the full OpenAgua documentation at [http://docs.openagua.org](http://docs.openagua.org).

# Setup/run on a local machine

These setup instructions are general, for both Windows and Linux. This is untested on OSX, but presumably setup should be similar to that for Linux.

OpenAgua connects to Hydra Platform. So, Hydra Platform needs to be available, either locally or remotely. This assumes Hydra Platform will be run locally. In this case, the first step is to make sure Hydra Platform is running, after which OpenAgua may be run.

**IMPORTANT**: For the time being, even a local setup requires an internet connection, to load externally-hosted JavaScript libraries. This will change in the future.

## Hydra Platform
* [general Hydra Platform information] (http://umwrg.github.io/HydraPlatform/),
* [download from GitHub] (https://github.com/openagua/hydraplatform), or
* [set up on Windows] (http://umwrg.github.io/hydraplatform/tutorials/getting-started/server.html)
* **IMPORTANT**: Hydra Platform requires Python 2.7, but OpenAgua requires Python 3.5. This needs to be accounted for, either by changing batch file scripts used to run the respective applications, or setting up virtual environments. On Windows, for example, if Python 3.5 is your main Python, you can change the second-to-last line of *run_server.bat* (found in `/Hydra Platform/Hydra Server/`) to something like `C:\python27\python server.py`, depending on where Python 2.7 is installed.

## OpenAgua

### Install

OpenAgua was built on Python 3.5, so this should be installed first. Earlier versions of Python 3 might also work, but there's no guarantee. Other requirements follow.

#### Python modules

For requirements, please see `requirements.txt`, which is built automatically using pip.

To install requirements: `pip install -r requirements.txt`

#### JavaScript

For the time being, no distributed JavaScript libraries are included in this repository. This means they must be compiled first. Generally, this entails: 1) installing dependent libraries from [npm](https://www.npmjs.com/) and 2) compiling with [webpack](https://webpack.js.org/).

1. Install from npm. This requires [Node.js](https://nodejs.org) (which includes npm) and [Yarn](https://yarnpkg.com/en/) (an installation tool that builds on npm). 
* Install Node.js: https://nodejs.org/en/download/ (or from a package manager: https://nodejs.org/en/download/package-manager/).
* Install Yarn: https://yarnpkg.com/lang/en/docs/install/
* Now, from the root OpenAgua folder run `yarn`, which will read _package.json_ and import requirements into _node_modules_.
2. Compile with webpack (installed from the above process):
* Windows (development): `.\node_modules\.bin\webpack --config webpack.config.js` (included in _webpack.bat_)
* Linux (production): `./node_modules/.bin/webpack --config webpack.config.js -p --progress` (included in _webpack.sh_)

#### Windows issues:

No specific issues.

#### Linux issues:

Two potential issues exist, but others may also exist (consult Google if troubles arise, and let us know so we can document the issues here!):

1. *pip3* should be used instead of *pip* (for installing Python 3.x modules). At least on Amazon's default Ubuntu, *pip3* is not installed by default, so this should be installed: `sudo apt-get install pip3`.

2. Encryption-related modules may need to be compiled during installation. Consult the Internet if trouble arises.

### Modify settings

Settings are found in the top-level config.py. An explanation of all settings is found below.

There are a few settings that should be set on a machine-specific basis, whether on a local machine or on a web server. These are stored in a folder called "instance" under the top-level OpenAgua folder:

1. Create an "/instance" folder. This folder stores machine-specific settings and the user database.
2. In "/instance", create "config.py". This new file contains settings that will supercede settings in the main "config.py". For example, you can overwrite default debug settings, as: `DEBUG=True`.
3. At a minimum, set the following parameters (values are examples only; your settings may be different):
```
# Flask-Mail settings
MAIL_USERNAME = 'admin@mysite.com'
MAIL_PASSWORD = 'password'
MAIL_SERVER = 'smtp.mysite.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USE_TLS = False
```
NB: This assumes email confirmation is needed. However, if a local machine is used, email confirmation can be switched off with `SECURITY_LOGIN_WITHOUT_CONFIRMATION = True` in config.py (This needs to be confirmed!).

Optionally, set other parameters as desired. For example, the OpenAgua user database (`OA_DATABASE_URI`) can be specified here. For SQLite, see the example in the default config.py file. For MySQL: `mysql+pymysql://username:password@xxxxx.xxxxx.com/dbname`.

Note that SECRET_KEY can be created in Python with the urandom function in the os module. I.e. `import os` followed by `os.urandom(24)`. IMPORTANT: This should be set in `\instance\config.py` in a production environment!

#### Instance settings and keys:
Here are keys that should be included in instance/instance_config.py, as of 18-04-2018:

ORGANIZATION = None

INCLUDE_HYDROLOGY = True # flag to include hydrology features; out-of-date, so not strictly needed

DATA_ROOT_PASSWORD = '...' # root password for Hydra Platform  
SECRET_ENCRYPT_KEY = b'a_secret_key'

**MAIL SETTINGS - these can be experimented with**

**Flask-Security**

SECURITY_PASSWORD_HASH = 'sha256_crypt'  
SECURITY_PASSWORD_SALT = '...'  
SECURITY_EMAIL_SENDER = 'abc@xyz.com'  
SECURITY_CONFIRMABLE = True  
SECURITY_SEND_REGISTER_EMAIL = True  
SECURITY_LOGIN_WITHOUT_CONFIRMATION = False  
SECURITY_REGISTERABLE = True  
SECURITY_RECOVERABLE = True  
SECURITY_TRACKABLE = False  
SECURITY_PASSWORDLESS = False  
SECURITY_CHANGEABLE = True

MAIL_USERNAME = 'abc@gmail.com'  
MAIL_PASSWORD = 'agr8password!'  
MAIL_SERVER = 'smtp.server.com'  
MAIL_PORT = 465  
MAIL_USE_SSL = True

**Mapbox**

MAPBOX_USERNAME = 'drheinheimer'  
MAPBOX_DISCOVERY_TILESET_NAME = 'openagua_networks'  
MAPBOX_ACCESS_TOKEN = '...'  
MAPBOX_CREATION_TOKEN = '...'  
MAPBOX_DATASET_NAME = 'abcde' # this is the dataset for uploading networks to Mapbox; not needed for installation  
MAPBOX_DISCOVER_MAP = 'drheinheimer/cj33tf0ea00432srzd899tmpz'

**Google places**

GOOGLE_PLACES_API_KEY = '...' # for places search and Google maps

**Google Earth Engine - to aid in watershed delineation**

EE_SERVICE_ACCOUNT_ID = '...'  
EE_PRIVATE_KEY = 'OpenAgua-xxxxxxxxxxx.json'

**AWS - for adding cloud computers and accessing S3**

USE_AWS = True  
AWS_ACCOUNT_ID = '12345'  
AWS_SSH_SECURITY_GROUP = 'sg-12345'  
AWS_DEFAULT_REGION = 'us-west-2'  
AWS_ACCESS_KEY_ID = 'ABC' # for AWS access, especially S3  
AWS_SECRET_ACCESS_KEY = 'xyz'  
AMI_ID = 'ami-16814c6e' # default AMI ID for modeling (not used)

**Locize.com - for translations; not used yet**

LOCIZE_PROJECT_ID = 'abc'  
LOCIZE_API_KEY = 'xyz'

**Handsontable**

### Create user database

To create the initial user database, from the main OpenAgua directory, execute the following commands sequentially:

1. `python manage.py db init`
2. `python manage.py db migrate`
3. `python manage.py db upgrade`

### Create admin user

To create an admin user, from the main OpenAgua directory execute `python manage.py addsuperuser`. You will then be prompted to add an email address and password for the account. If you want to cancel the process, just hit enter a few times to exit.

## Run

1. Run Hydra Platform, or make sure DATA_URL points to a working Hydra Platform server (Hydra Server).
2. Run OpenAgua/run.py (`python run.py`, or `run.bat` on Windows)
3. Go to http://localhost:5000 in your web browser.
4. Register and/or login. Note that internet access is required during registration, as an email confirmation is sent for confirmation during the process.

# Setup/serve as web server

This assumes Hydra Platform and OpenAgua are run from the same Ubuntu Linux machine, and where OpenAgua is served to the world by uwsgi+nginx. The general setup process is described, followed by configurations as used on www.openagua.org.

**NOTE 1**: This will all be smoothed out in the future with the development of docker images for both OpenAgua and Hydra Platform.

**NOTE 2**: The description below is somewhat out of date, as OpenAgua now uses socket.io for real-time communications between the web server and client; this needs to be accounted for in the nginx setup.

## General process
The setup process can be broken down into the following steps:

1. Install nginx
2. Set up each respective base application (i.e., Hydra Platform and OpenAgua). For each application:
  a. Download the application
  b. Set up a virtual environment
  c. Install required Python packages within the virtual environment
  d. Install uwsgi from within the virtual environment
  e. Configure the application
  f. Create and configure a wsgi.py file to serve the application
  g. Create and configure a uWSGI configuration file
  h. Create and configure an application service
  i. Create, configure and enable nginx site
3. Start each application service
4. Start nginx
5. Update the site and restart services as needed

NOTE: Much of this information is as described on this helpful DigitalOcean article, [How To Serve Flask Applications with uWSGI and Nginx on Ubuntu 16.04](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04).

## Setup for www.openagua.org

### 1. Nginx

For now, really just install nginx: `sudo apt-get install nginx`

### 2. Set up each respective application.

#### Hydra Platform

a. Download Hydra Platform from GitHub as described above.

b. For the virtual environment, `virtuanenvwrapper` works well. See [virtualenvwrapper docs](https://virtualenvwrapper.readthedocs.io/en/latest/). In the end, you should type `mkvirtualenv hydraplatform` followed by `workon hydraplatform` as needed.

c. In the virtual environment for Hydra Platform, install dependencies (using `pip`) as described at https://github.com/UMWRG/HydraPlatform#hydraplatform. Some pointers for installing on Ubuntu:
* For mysql-connector-python: `sudo apt-get install python-mysql.connector`
* For bcrypt, make sure to install python-dev first: `sudo apt-get install python-dev`

d. Install uwsgi. From within the virtual environment: `pip install uwsgi`

e. Configure Hydra Platform:
* Specify the database that Hydra Platform will use in /HydraPlatform/config/hydra.ini.
* Create a new HydraServer folder next to HydraPlatform. This will hold the local configurations for running Hydra Server without affecting the original Hydra Platform.

f. In the case of Hydra Platform wsgi.py can just create a symbolic link directly to Hydra Server. From within the new HydraServer directory:
```
ln -s ../HydraPlatform/HydraServer/server.py wsgi.py
```

g. Create and configure uWSGI configuration file:

Create:
```
sudo nano /home/ubuntu/HydraServer/hydraserver.ini
```

Configure contents:
```
[uwsgi]
wsgi-file = wsgi.py

master = true
processes = 1

socket = hydraserver.sock
chmod-socket = 660
vacuum = true

die-on-term = true

logto = error.log
```
**IMPORTANT**: Processes should increase in the future once Hydra Server supports this.

h. Create/configure the application service:

Create:
```
sudo nano /etc/systemd/system/hydraserver.service
```

Configure contents:
```
[Unit]
Description=uWSGI instance to serve HydraServer
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/HydraServer
Environment="PATH=/home/ubuntu/Env/hydraserver/bin"
Environment="PYTHONPATH=${PYTHONPATH}:/home/ubuntu/HydraPlatform/HydraLib/python:/home/ubuntu/HydraPlatform/HydraServer/python"
ExecStart=/home/ubuntu/Env/hydraserver/bin/uwsgi --ini hydraserver.ini

[Install]
WantedBy=multi-user.target
```

i. Create/configure the nginx site:

Create:
```
sudo nano /etc/nginx/sites-available/hydraplatform
```

Configure contents:
```
server {
    listen 80;
    listen [::]80;
    server_name data.openagua.org;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/ubuntu/HydraServer/hydraserver.sock;
    }
}

```

Enable site with a symbolic link:
```
sudo ln -s /etc/nginx/sites-available/hydraplatform /etc/nginx/sites-enabled/hydraplatform
```

#### OpenAgua

a. Install OpenAgua using git: From /var/www type `sudo git clone https://github.com/CentroDelAgua/OpenAgua.git`

b. Set up virtual environment

c. Install packages

d. Install uwsgi

e. Configure the application [OBSOLETE - TO BE UPDATED]:
* Set up /instance/config.py. In addition to the settings as described above, make sure to add:
        * DATA_URL (e.g., `DATA_URL = 'http://hydra-server.mysite.com/json'`)
        * SECRET_KEY

f. wsgi.py:

Create:
```
nano /home/ubuntu/OpenAgua/wsgi.py
```

Configure:
```
from OpenAgua import app

if __name__ == "__main__":
    app.run()
```

g. wsgi service configuration:

Create:
```
nano /home/ubuntu/OpenAgua/openagua.ini
```

Configure:
```
[uwsgi]
module = wsgi:app

master = true
processes = 5

socket = openagua.sock
chmod-socket = 660
vacuum = true

die-on-term = true

logto = instance/error.log
```

h. System service:

Create:
```
sudo nano /etc/systemd/system/openagua.service
```
Configure:
```
[Unit]
Description=uWSGI instance to serve OpenAgua
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/OpenAgua
Environment="PATH=/home/ubuntu/Env/openagua/bin"
ExecStart=/home/ubuntu/Env/openagua/bin/uwsgi --ini openagua.ini

[Install]
WantedBy=multi-user.target
```

i. nginx site:

Create:
```
sudo nano /etc/nginx/sites-available/openagua
```

Configure:
```
server {
    listen 80;
    listen [::]80;
    server_name test.openagua.org;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/ubuntu/OpenAgua/openagua.sock;
    }
}
```

Enable:
```
sudo ln -s /etc/nginx/sites-available/openagua /etc/nginx/sites-enabled/openagua
```

3. Start and enable the application services:

Hydra Platform:
```
sudo systemctl start hydraserver
sudo systemctl enable hydraserver
```

OpenAgua:
```
sudo systemctl start openagua
sudo systemctl enable openagua
```

4. Start (restart) nginx:

To start: `sudo service nginx start`

To stop: `sudo service nginx stop` (or `sudo killall -9 nginx`)

To restart: `sudo service nginx restart`

5. Update the website & services as needed.

a. GitHub contents can be easily updated. From within OpenAgua: `git pull`

b. The web applications can also be easily restarted: E.g.:
```
sudo systemctl restart openagua.service
```

There is no need to restart nginx.

# Settings

[To be completed]

# Encryption

[Let's Encrypt](https://letsencrypt.org) offers free encryption certificates, which can easily be installed by following the guide at using [Certbot](https://certbot.eff.org).

For example, for Nginx on Ubuntu 16.04, the general process is as follows (see [Certbot](https://certbot.eff.org) for OS-specific instructions):

1. Install Certbot ("Install")

```
$ sudo apt-get update
$ sudo apt-get install software-properties-common
$ sudo add-apt-repository ppa:certbot/certbot
$ sudo apt-get update
$ sudo apt-get install python-certbot-nginx 
```

2. Obtain the certificate ("Get Started")

`sudo certbot --nginx`

3. Periodically renew the certificate ("Automating Renewal")

The `certbot renew` command is used to renew certificates. Certbot recommends running this twice per day, at random times. In Linux, `cron` is used to schedule tasks. To add a cron task, use crontab:

`sudo crontab -e`

To run `certbot renew` at random times within the noon and midnight hours, add the following to the crontab file:

`0 0,12 * * * sleep $(( RANDOM \% 3600 )); certbot renew`

Save this, and that's it! You're golden.