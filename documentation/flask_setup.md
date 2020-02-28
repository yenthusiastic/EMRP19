### Flask Web Server Setup Guide
#### 1. Installations
- Pre-requisites:
    - Python 3.7

- Download the whole content of the [web-ui](https://github.com/yenthusiastic/EMRP19/tree/master/code/web-ui) folder containing souce codes of the web management interface.
- To install all dependencies of the web management interface, open Command Prompt (Windows) or Terminal (Linux) inside the `webui` folder and run the following command:
    ```
    pip install -r requirements.txt
    ```
#### 2. Launch Flask web server
- To launch the web server, open Command Prompt (Windows) or Terminal (Linux) inside the `webui` folder and run the following command:
    ```
    python app.py
    ```
    Press `Ctrl+C` to terminate the application when desired. To run the application in the background the following commands can be used: 
    ```
    screen -S flask_server
    python app.py
    ```
    Press `Ctrl + A` then `D` to detach the screen session while keep it running in the background. To reattach the session, run `screen -r flask_server`.

- The web interface can now be accessible at [http://localhost:5022/](http://localhost:5022/).
