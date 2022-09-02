import random, time, os, threading, json
from pprint import pprint
from datetime import datetime, timedelta
import subprocess
import paho.mqtt.client as mqtt


def get_room_id():
    host = subprocess.check_output(['bash', '-c', 'echo $HOSTNAME']).decode("utf-8")[0:-1]
    print("The host name of this room is", host)
    return host


room_number = ""
connection_pw = False
telemetry_topics = [["temperature", "value"], ["air-conditioner", "state", "value"],
                    ["presence", "detected"], ["indoor-light", "state", "intensity"],
                    ["outdoor-light", "state", "intensity"], ["blinds", "degree"]]
CONFIG_TOPIC_MR = "/hotel/rooms/" + get_room_id() + "/config"
TELEMETRY_TOPIC_MR = "/hotel/rooms/" + room_number + "/telemetry/"
TELEMETRY_TOPIC_PW = "/hotel/p_rooms/" + room_number + "/telemetry/"
CONFIG_TOPIC_PW = "/hotel/p_rooms/" + room_number + "/config"
COMMAND_TOPIC = "/hotel/rooms/" + room_number + "/command/+"
CONNECTION_TOPIC = "/hotel/p_rooms/" + room_number + "/connection"
MQTT_server = os.getenv("MQTT_SERVER_ADDRESS")
MQTT_port_mr = int(os.getenv("MQTT_SERVER_PORT_MR"))
MQTT_port_pw = int(os.getenv("MQTT_SERVER_PORT_PW"))
RANDOMIZE_SENSORS_INTERVAL = 60  # seconds
random_sensors = None
air_states = ["Stop", "Heating", "Cooling"]
light_states = ["On", "Off"]
current_air_mode = ""
current_indoor_mode = ""
current_indoor_value = 0
current_outdoor_mode = ""
current_outdoor_value = 0
current_blinds = 0

sensors = {
    "air-conditioner": {
        "state": air_states[random.randint(0, 2)],
        "value": random.randint(0, 100)
    },
    "presence": {
        "detected": 1 if random.randint(0, 1) == 1 else 0
    },
    "temperature": {
        "value": random.randint(-10, 40)
    },
    "indoor-light": {
        "state": light_states[random.randint(0, 1)],
        "intensity": random.randint(0, 100)
    },
    "outdoor-light": {
        "state": light_states[random.randint(0, 1)],
        "intensity": random.randint(0, 100)
    },
    "blinds": {
        "degree": random.randint(0, 180)
    }
}


def randomize_sensors():
    global sensors, air_states, light_states, random_sensors
    sensors = {
        "air-conditioner": {
            "state": air_states[random.randint(0, 2)],
            "value": random.randint(0, 100)
        },
        "presence": {
            "detected": 1 if random.randint(0, 1) == 1 else 0
        },
        "temperature": {
            "value": random.randint(-10, 40)
        },
        "indoor-light": {
            "state": light_states[random.randint(0, 1)],
            "intensity": random.randint(0, 100)
        },
        "outdoor-light": {
            "state": light_states[random.randint(0, 1)],
            "intensity": random.randint(0, 100)
        },
        "blinds": {
            "degree": random.randint(0, 180)
        }
    }

    if not connection_pw:
        print("Set randomize sensors")
        pprint(sensors)
        for topic in telemetry_topics:
            publish_sensor_state(topic)
        threading.Timer(RANDOMIZE_SENSORS_INTERVAL, randomize_sensors).start()
    else:
        print("Stopping the sendall of random telemetry values")


def on_connect_mr(client, userdata, flags, rc):
    if rc == 0:
        print("Digital Twin connected to message router MQTT with code", rc)
        room_id = get_room_id()
        client.publish(CONFIG_TOPIC_MR, payload=room_id, qos=0, retain=False)
        print("Sent ID", room_id, "to topic", CONFIG_TOPIC_MR)
        client.subscribe(CONFIG_TOPIC_MR + "/room")
        print("Subscribed to", CONFIG_TOPIC_MR + "/room")
    else:
        print("Error connecting. Retry connection")


def on_connect_pw(client, userdata, flags, rc):
    global client_pw, CONFIG_TOPIC_PW, TELEMETRY_TOPIC_PW, CONNECTION_TOPIC
    if rc == 0:
        print("Digital Twin connected to physical world MQTT with code", rc)
        client_pw.subscribe(CONFIG_TOPIC_PW)
        print("Subscribed to", CONFIG_TOPIC_PW)
        client_pw.subscribe(CONNECTION_TOPIC)
        print("Subscribed to", CONNECTION_TOPIC)
    else:
        print("Error connecting. Retry connection")


def on_message_mr(client, userdata, msg):
    global room_number, TELEMETRY_TOPIC_MR, CONFIG_TOPIC_PW, TELEMETRY_TOPIC_PW, COMMAND_TOPIC, client_pw, CONNECTION_TOPIC
    topic = msg.topic.split("/")
    if "config" in topic:
        room_number = msg.payload.decode()
        print("Room number received as:", room_number)
        TELEMETRY_TOPIC_MR = "/hotel/rooms/" + room_number + "/telemetry/"
        TELEMETRY_TOPIC_PW = "/hotel/p_rooms/" + room_number + "/telemetry/"
        CONFIG_TOPIC_PW = "/hotel/p_rooms/" + room_number + "/config"
        CONNECTION_TOPIC = "/hotel/p_rooms/" + room_number + "/connection"
        COMMAND_TOPIC = "/hotel/rooms/" + room_number + "/command/+"
        client.subscribe(COMMAND_TOPIC)
        print("Subscribed to command topics", COMMAND_TOPIC)
        connection_topic = "/hotel/rooms/" + room_number + "/connection"
        date = (datetime.now() + timedelta(hours=2)).isoformat()
        json_data = {"room": room_number, "type": "digital", "date": date, "state": "Active"}
        client.publish(connection_topic, payload=json.dumps(json_data), qos=0, retain=False)
        print("Send connection state to message router")
    elif "command" in topic:
        if topic[-1] == "air_conditioner":
            global current_air_mode
            payload = json.loads(msg.payload)
            if payload["state"] == 0:
                air_mode_command = "Cooling"
            elif payload["state"] == 1:
                air_mode_command = "Heating"
            elif payload["state"] == 2:
                air_mode_command = "Stop"
            else:
                air_mode_command = "Auto"
            print("Command received for air-conditioner")
            if air_mode_command != current_air_mode:
                json_data = {"state": air_mode_command}
                client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/air_conditioner",
                                  payload=json.dumps(json_data), qos=0, retain=True)
                current_air_mode = air_mode_command
                print("Publish data to Raspberry from command")
        if topic[-1] == "indoor_light":
            global current_indoor_mode, current_indoor_value
            payload = json.loads(msg.payload)
            if "state" in payload:
                if int(payload["state"]) == 0:
                    indoor_mode_command = "On"
                else:
                    indoor_mode_command = "Off"
                print("Command received for indoor light state")
                if indoor_mode_command != current_indoor_mode:
                    json_data = {"state": indoor_mode_command}
                    client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/indoor_light_state",
                                      payload=json.dumps(json_data), qos=0, retain=True)
                    current_indoor_mode = indoor_mode_command
                    print("Publish data to Raspberry from command")
            else:
                print("Command received for indoor light value")
                if payload["value"] != current_indoor_value:
                    json_data = {"value": payload["value"]}
                    client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/indoor_light_value",
                                      payload=json.dumps(json_data), qos=0, retain=True)
                    current_indoor_value = payload["value"]
                    print("Publish data to Raspberry from command")
        if topic[-1] == "outdoor_light":
            global current_outdoor_mode, current_outdoor_value
            payload = json.loads(msg.payload)
            if "state" in payload:
                if int(payload["state"]) == 0:
                    outdoor_mode_command = "On"
                else:
                    outdoor_mode_command = "Off"
                print("Command received for outdoor light state")
                if outdoor_mode_command != current_outdoor_mode:
                    json_data = {"state": outdoor_mode_command}
                    client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/outdoor_light_state",
                                      payload=json.dumps(json_data), qos=0, retain=True)
                    current_outdoor_mode = outdoor_mode_command
                    print("Publish data to Raspberry from command")
            else:
                print("Command received for outdoor light value")
                if payload["value"] != current_outdoor_value:
                    json_data = {"value": payload["value"]}
                    client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/outdoor_light_value",
                                      payload=json.dumps(json_data), qos=0, retain=True)
                    current_outdoor_value = payload["value"]
                    print("Publish data to Raspberry from command")
        if topic[-1] == "blinds":
            global current_blinds
            payload = json.loads(msg.payload)
            print("Command received for blinds degree")
            if payload["degree"] != current_blinds:
                json_data = {"value": payload["degree"]}
                client_pw.publish("/hotel/p_rooms/" + topic[3] + "/command/blinds",
                                  payload=json.dumps(json_data), qos=0, retain=True)
                current_outdoor_value = payload["degree"]
                print("Publish data to Raspberry from command")


def on_message_pw(client, userdata, msg):
    global connection_pw, telemetry_topics, TELEMETRY_TOPIC_PW, random_sensors, client_mr
    print("Message received in", msg.topic, "with message", msg.payload.decode())
    topic = msg.topic.split('/')
    if topic[-1] == "config":
        print("Physical room number", msg.payload.decode(), "successfully connected")
        connection_pw = True
        for topic in telemetry_topics:
            client_pw.subscribe(TELEMETRY_TOPIC_PW + topic[0])
            print("Subscribed to all telemetry topics from PW", TELEMETRY_TOPIC_PW + topic[0])
        client_pw.publish(msg.topic + "/room", payload=msg.payload.decode(), qos=0, retain=True)
        print("Resent room number", msg.payload.decode(), "for acknowledgement to", msg.topic)
    elif topic[-1] == "temperature":
        publish_sensor_state("temperature", msg.payload.decode())
    elif topic[-1] == "presence":
        publish_sensor_state("presence", msg.payload.decode())
    elif topic[-1] == "air-conditioner":
        global current_air_mode
        json_data = json.loads(msg.payload.decode())
        current_air_mode = json_data["state"]
        publish_sensor_state("air-conditioner", msg.payload.decode())
    elif topic[-1] == "indoor_light":
        global current_indoor_mode, current_indoor_value
        json_data = json.loads(msg.payload.decode())
        current_indoor_mode = json_data["state"]
        current_indoor_value = json_data["intensity"]
        publish_sensor_state("indoor-light", msg.payload.decode())
    elif topic[-1] == "outdoor_light":
        global current_outdoor_mode, current_outdoor_value
        json_data = json.loads(msg.payload.decode())
        current_outdoor_mode = json_data["state"]
        current_outdoor_value = json_data["intensity"]
        publish_sensor_state("outdoor-light", msg.payload.decode())
    elif topic[-1] == "blinds":
        global current_blinds
        json_data = json.loads(msg.payload.decode())
        current_blinds = json_data["degree"]
        publish_sensor_state("blinds", msg.payload.decode())
    elif topic[-1] == "connection":
        connected = msg.payload.decode()
        topic_c = "/hotel/rooms/" + topic[3] + "/connection"
        client_mr.publish(topic_c, payload=connected, qos=0, retain=False)
        print("Added connection state", connected, "for physical room", topic[3], "successfully")


def on_publish(client, userdata, result):
    print("Data published")
    pass


def connect_mqtt_mr():
    global client_mr, room_number, random_sensors
    print("Set MQTT user and password for connection")
    client_mr.username_pw_set(username="dso_server", password="dso_password")
    print("Set on connect, on message and on publish handlers")
    client_mr.on_connect = on_connect_mr
    client_mr.on_message = on_message_mr
    client_mr.on_publish = on_publish
    print("Try connection")
    date = (datetime.now() + timedelta(hours=2)).isoformat()
    json_data = {"room": get_room_id(), "type": "digital", "date": date, "state": "Inactive"}
    connection_topic = "/hotel/rooms/" + get_room_id() + "/connection"
    client_mr.will_set(connection_topic, payload=json.dumps(json_data), qos=0, retain=False)
    client_mr.connect(MQTT_server, MQTT_port_mr, 60)
    client_mr.loop_forever()


def connect_mqtt_pw():
    global client_pw, room_number, connection_pw
    print("Waiting for room number from message router")
    while room_number == "":
        time.sleep(1)
    print("Room number received. Start connection with PW MQTT")
    print("Start random sensors sendall until physical room connects")
    randomize_sensors()
    print("Set MQTT user and password for connection with PW")
    client_pw.username_pw_set(username="dso_server", password="dso_password")
    print("Set on connect, on message and on publish handlers")
    client_pw.on_connect = on_connect_pw
    client_pw.on_message = on_message_pw
    client_pw.on_publish = on_publish
    print("Try connection")
    client_pw.connect(MQTT_server, MQTT_port_pw, 60)
    client_pw.loop_forever()


def publish_sensor_state(topic, payload=""):
    global client_mr, connection_pw
    if not connection_pw:
        parameters = topic[1:]
        json_dict = {}
        for param in parameters:
            json_dict[param] = sensors[topic[0]][param]
        json_dict["date"] = (datetime.now() + timedelta(hours=2)).isoformat()
        json_data = json.dumps(json_dict)
        client_mr.publish(TELEMETRY_TOPIC_MR + topic[0], payload=json_data, qos=0, retain=False)
        print("Published", json_data, "in", TELEMETRY_TOPIC_MR + topic[0])
    else:
        client_mr.publish(TELEMETRY_TOPIC_MR + topic, payload=payload, qos=0, retain=False)
        print("Published", payload, "in", TELEMETRY_TOPIC_MR + topic)


if __name__ == "__main__":
    client_mr = mqtt.Client()
    client_pw = mqtt.Client()

    t_message_router = threading.Thread(target=connect_mqtt_mr)
    t_physical_world = threading.Thread(target=connect_mqtt_pw)

    t_message_router.setDaemon(True)
    t_physical_world.setDaemon(True)

    t_message_router.start()
    t_physical_world.start()

    t_message_router.join()
    t_physical_world.join()
