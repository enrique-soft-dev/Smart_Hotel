import json

from flask import Flask, request
from flask_cors import CORS
from data_ingestion import *
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)


@app.route('/device_state', methods=['GET', 'POST'])
def device_state():
    if request.method == 'POST':
        params = request.get_json()
        if len(params) == 4:
            my_cursor = insert_device_state(params)
            return {"response": f"{my_cursor} records inserted."}, 200
        return {"response": "Incorrect parameters"}, 401
    elif request.method == 'GET':
        devices_data = []
        for i in range(1, 41):
            devices_data.extend(get_devices_states("Room-" + str(i)))
        return json.dumps(devices_data), 200


@app.route('/connection', methods=['POST'])
def connection():
    if request.method == "POST":
        params = request.get_json()
        if len(params) == 4:
            if params["value"] == "Inactive":
                params["date"] = (datetime.now() + timedelta(hours=2)).isoformat()
                my_cursor = update_connection(params)
            else:
                already_connected = check_connection(params["room"], params["type"])
                if already_connected:
                    my_cursor = update_connection(params)
                else:
                    my_cursor = insert_connection(params)
            return {"response": f"{my_cursor} connection inserted."}, 200
        return {"response": "Incorrect parameters"}, 401


HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
app.run(host=HOST, port=PORT, debug=False)
