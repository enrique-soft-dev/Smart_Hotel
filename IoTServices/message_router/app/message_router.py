import json
import os
import threading

import paho.mqtt.client as mqtt
import requests
from flask import Flask, request
from flask_cors import CORS
from datetime import datetime, timedelta

ALL_TOPICS = "/hotel/rooms/+/telemetry/+"
CONFIG_TOPIC = "/hotel/rooms/+/config"
CONNECTION_TOPIC = "/hotel/rooms/+/connection"
MQTT_server = os.getenv("MQTT_SERVER_ADDRESS")
MQTT_port = int(os.getenv("MQTT_SERVER_PORT"))
API_URL = "http://" + os.getenv("API_SERVER_ADDRESS") + ":" + os.getenv("API_SERVER_PORT")
API_HOST = os.getenv("API_HOST")
API_PORT = os.getenv("API_PORT")

room_index = 1
current_temperature = "0"
current_air = "0"
current_blind = "0"
current_indoor_light = "0"
current_outside_light = "0"
current_presence = "0"
saved_rooms = {}
app = Flask(__name__)


def on_connect(client, userdata, flags, rc):
    """connecting (subscribing) to all topics at once"""
    if rc == 0:
        print("Connected on subscriber with code", rc)
        client.subscribe(ALL_TOPICS)
        client.subscribe(CONFIG_TOPIC)
        client.subscribe(CONNECTION_TOPIC)
        print("Subscribed to all telemetry topics")
        print("Subscribed to all config")
        print("Subscribed to all connections topics")
    else:
        print("Connection failed on subscriber with code", rc)


def on_message(client, userdata, msg):
    global current_temperature, current_air, current_blind, current_indoor_light, current_outside_light,\
        current_presence, room_index, saved_rooms
    print("Message received in", msg.topic, "with message", msg.payload.decode())
    topic = msg.topic.split('/')
    if topic[-1] == "config":
        if saved_rooms.get(msg.payload.decode()) is None:
            room_name = "Room-" + str(room_index)
            saved_rooms[msg.payload.decode()] = room_name
            print("Digital twin with id", msg.payload.decode(), "saved as", room_name)
            client.publish(msg.topic + "/room", payload=room_name, qos=0, retain=True)
            print("Published", room_name, "in topic", msg.topic + "/room")
            room_index += 1
    elif topic[-1] == "temperature":
        current_temperature = msg.payload.decode()
        data = json.loads(current_temperature)
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "temperature", "value": data["value"], "date": data["date"]})
        print("Added temperature", current_temperature, "for room", topic[-3], "successfully")
    elif topic[-1] == "air-conditioner":
        current_air = msg.payload.decode()
        data = json.loads(current_air)
        if data["state"] == "Stop":
            value = 2
        elif data["state"] == "Cooling":
            value = 0
        elif data["state"] == "Heating":
            value = 1
        else:
            value = 3
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "air-state", "value": value, "date": data["date"]})
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "air-level", "value": data["value"], "date": data["date"]})
        print("Added air-conditioner", current_air, "for room", topic[-3], "successfully")
    elif topic[-1] == "blinds":
        current_blind = msg.payload.decode()
        data = json.loads(current_blind)
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "blind-degree", "value": data["degree"], "date": data["date"]})
        print("Added blind", current_blind, "for room", topic[-3], "successfully")
    elif topic[-1] == "indoor-light":
        current_indoor_light = msg.payload.decode()
        data = json.loads(current_indoor_light)
        if data["state"] == "On":
            value = 0
        else:
            value = 1
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "indoor-state", "value": value, "date": data["date"]})
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "indoor-value", "value": data["intensity"], "date": data["date"]})
        print("Added indoor light", current_indoor_light, "for room", topic[-3], "successfully")
    elif topic[-1] == "outdoor-light":
        current_outside_light = msg.payload.decode()
        data = json.loads(current_outside_light)
        if data["state"] == "On":
            value = 0
        else:
            value = 1
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "outdoor-state", "value": value, "date": data["date"]})
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "outdoor-value", "value": data["intensity"], "date": data["date"]})
        print("Added outside light", current_outside_light, "for room", topic[-3], "successfully")
    elif topic[-1] == "presence":
        current_presence = msg.payload.decode()
        data = json.loads(current_presence)
        requests.post(API_URL + "/device_state", json={"room": topic[3], "type": "presence", "value": data["detected"], "date": data["date"]})
        print("Added presence", current_presence, "for room", topic[-3], "successfully")
    elif topic[-1] == "connection":
        connected = msg.payload.decode()
        data = json.loads(connected)
        if "Room" not in data["room"]:
            room = saved_rooms[data["room"]]
        else:
            room = data["room"]
        requests.post(API_URL + "/connection", json={"room": room, "type": data["type"], "value": data["state"], "date": data["date"]})
        print("Added connection state", connected, "for room", room, "successfully")


def do_connect():
    global client
    print("Set MQTT user and password for connection")
    client.username_pw_set(username="dso_server", password="dso_password")
    print("Set on connect and on message handlers")
    client.on_connect = on_connect
    client.on_message = on_message
    print("Try connection")
    client.connect(MQTT_server, MQTT_port, 60)
    client.loop_forever()


def send_command(params):
    global client
    type_dev = params["type"]
    value = params["value"]
    room = params["room"]
    date = (datetime.now() + timedelta(hours=2)).isoformat()
    print(type_dev, value, room)
    if type_dev == "air-state":
        topic = "/hotel/rooms/" + room + "/command/air_conditioner"
        json_data = {"state": int(value)}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        print("Command message sent through", topic)
        return {"response": "Message for air mode sent successfully"}, 200
    elif type_dev == "indoor-value":
        topic = "/hotel/rooms/" + room + "/command/indoor_light"
        json_data = {"value": value}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        return {"response": "Message for indoor light intensity sent successfully"}, 200
    elif type_dev == "indoor-state":
        topic = "/hotel/rooms/" + room + "/command/indoor_light"
        json_data = {"state": value}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        return {"response": "Message for indoor light mode sent successfully"}, 200
    elif type_dev == "outdoor-value":
        topic = "/hotel/rooms/" + room + "/command/outdoor_light"
        json_data = {"value": value}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        return {"response": "Message for outdoor light value sent successfully"}, 200
    elif type_dev == "outdoor-state":
        topic = "/hotel/rooms/" + room + "/command/outdoor_light"
        json_data = {"state": value}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        return {"response": "Message for outdoor light mode sent successfully"}, 200
    elif type_dev == "blind-degree":
        topic = "/hotel/rooms/" + room + "/command/blinds"
        json_data = {"degree": value}
        client.publish(topic, payload=json.dumps(json_data), qos=0, retain=True)
        requests.post(API_URL + "/device_state", json={"room": room, "type": type_dev, "value": value, "date": date})
        return {"response": "Message for blinds degree sent successfully"}, 200
    else:
        return {"response": "Incorrect type params"}, 401


@app.route("/device_state", methods=["POST"])
def device_state():
    if request.method == "POST":
        params = request.get_json()
        return send_command(params)


if __name__ == "__main__":
    client = mqtt.Client()
    mqtt_thread = threading.Thread(target=do_connect)
    mqtt_thread.setDaemon(True)
    mqtt_thread.start()

    CORS(app)
    app.run(host=API_HOST, port=API_PORT, debug=False)
