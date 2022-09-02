import time
import Adafruit_DHT
import datetime
from datetime import date, datetime
import threading
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import json

# Variable to kill threads
kill = False

# Pins for Motor Driver Inputs
Motor1A = 24
Motor1B = 23
Motor1E = 25

# set red, green and blue pins
redPin = 12
greenPin = 19
bluePin = 13

# set pin for button
buttonPin = 16

# Semaphore initialization
sem = threading.Semaphore(1)

# Create global for pwm
pwm = 0

# Set pin and pwm for indoor light
indoorPin = 17
indoorPWM = 0

# Set pin and pwm for outdoor light
outdoorPin = 27
outdoorPWM = 0

# Set pin and pwm for servomotor
servoPin = 22
servoPWM = 0

# Create variables for connection with MQTT
is_connected = False
MQTT_server = "34.159.251.54"
MQTT_port = 1884
CONFIG_TOPIC = "/hotel/p_rooms/Room-2/config"
TELEMETRY_TOPIC = "/hotel/p_rooms/Room-2/telemetry/"
COMMAND_TOPIC = "/hotel/p_rooms/Room-2/command/"

# Create sensors state
sensors = {
    "temperature": {
        "level": 0.0
    },
    "air-conditioner": {
        "state": "Auto",
        "level": 0
    },
    "presence": {
        "detected": False
    },
    "indoor_light": {
        "active": "Off",
        "intensity": 0
    },
    "outdoor_light": {
        "active": "Off",
        "intensity": 0
    },
    "blinds": {
        "degree": 0.0
    }
}

# Create global variable to control if the air conditioner acts automatically or not
automatic = True


def setup():
    # Set the mode of GPIO
    GPIO.setmode(GPIO.BCM)

    # Set motor pins
    GPIO.setup(Motor1A, GPIO.OUT)
    GPIO.setup(Motor1B, GPIO.OUT)
    GPIO.setup(Motor1E, GPIO.OUT)

    # Set led pins
    GPIO.setup(redPin, GPIO.OUT)
    GPIO.setup(greenPin, GPIO.OUT)
    GPIO.setup(bluePin, GPIO.OUT)

    # Set indoor pin and PWM
    GPIO.setup(indoorPin, GPIO.OUT)
    global indoorPWM
    indoorPWM = GPIO.PWM(indoorPin, 100)
    indoorPWM.start(0)

    # Set outdoor pin
    GPIO.setup(outdoorPin, GPIO.OUT)
    global outdoorPWM
    outdoorPWM = GPIO.PWM(outdoorPin, 100)
    outdoorPWM.start(0)

    # Set servomotor pin and PWM
    GPIO.setup(servoPin, GPIO.OUT)
    global servoPWM
    servoPWM = GPIO.PWM(servoPin, 50)
    servoPWM.start(0)

    # Set Motor1A to pwm based
    global pwm
    pwm = GPIO.PWM(Motor1A, 100)
    pwm.start(0)

    # Set button
    GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def ledThread(name):
    print("[+] Create the thread for:", name)
    global sem, kill, sensors, automatic

    while True:
        sem.acquire()
        if automatic:
            if sensors["presence"]["detected"]:
                if 21.0 <= sensors["temperature"]["level"] <= 24.0:
                    GPIO.output(redPin, GPIO.LOW)
                    GPIO.output(greenPin, GPIO.HIGH)
                    GPIO.output(bluePin, GPIO.LOW)
                elif sensors["temperature"]["level"] < 21.0:
                    GPIO.output(redPin, GPIO.HIGH)
                    GPIO.output(greenPin, GPIO.LOW)
                    GPIO.output(bluePin, GPIO.LOW)
                elif sensors["temperature"]["level"] > 24.0:
                    GPIO.output(redPin, GPIO.LOW)
                    GPIO.output(greenPin, GPIO.LOW)
                    GPIO.output(bluePin, GPIO.HIGH)
            else:
                GPIO.output(redPin, GPIO.LOW)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(bluePin, GPIO.LOW)
        else:
            if sensors["air-conditioner"]["state"] == "Cooling":
                GPIO.output(redPin, GPIO.LOW)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(bluePin, GPIO.HIGH)
            elif sensors["air-conditioner"]["state"] == "Heating":
                GPIO.output(redPin, GPIO.HIGH)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(bluePin, GPIO.LOW)
            elif sensors["air-conditioner"]["state"] == "Stop":
                GPIO.output(redPin, GPIO.LOW)
                GPIO.output(greenPin, GPIO.LOW)
                GPIO.output(bluePin, GPIO.LOW)

        if kill:
            sem.release()
            break
        sem.release()
        time.sleep(1)

    print("[-] Finish the thread for:", name)


def indoorLed(name):
    print("[+] Create the thread for:", name)
    global kill, sem, client_rp, is_connected, sensors, indoorPWM

    prev_state = "Off"
    prev_intensity = 0
    while True:
        sem.acquire()
        if sensors["indoor_light"]["active"] == "On":
            indoorPWM.ChangeDutyCycle(sensors["indoor_light"]["intensity"])
        else:
            indoorPWM.ChangeDutyCycle(0)

        if ((prev_state != sensors["indoor_light"]["active"] or prev_intensity != sensors["indoor_light"]["intensity"])
                and is_connected):
            if prev_state != sensors["indoor_light"]["active"]:
                if sensors["indoor_light"]["active"] == "On":
                    json_dict = {"state": sensors["indoor_light"]["active"],
                                 "intensity": sensors["indoor_light"]["intensity"],
                                 "date": datetime.now().isoformat()}
                    client_rp.publish(TELEMETRY_TOPIC + "indoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                    prev_intensity = sensors["indoor_light"]["intensity"]
                else:
                    json_dict = {"state": sensors["indoor_light"]["active"],
                                 "intensity": 0,
                                 "date": datetime.now().isoformat()}
                    client_rp.publish(TELEMETRY_TOPIC + "indoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                    prev_intensity = 0
            else:
                json_dict = {"state": sensors["indoor_light"]["active"],
                             "intensity": sensors["indoor_light"]["intensity"],
                             "date": datetime.now().isoformat()}
                client_rp.publish(TELEMETRY_TOPIC + "indoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                prev_intensity = sensors["indoor_light"]["intensity"]
            print("Indoor light data sent to digital twin")
            prev_state = sensors["indoor_light"]["active"]

        if kill:
            sem.release()
            break
        sem.release()
        time.sleep(1)

    print("[-] Finish the thread for:", name)


def outdoorLed(name):
    print("[+] Create the thread for:", name)
    global kill, sem, client_rp, is_connected, sensors, outdoorPWM

    prev_state = "Off"
    prev_intensity = 0
    while True:
        sem.acquire()
        if sensors["outdoor_light"]["active"] == "On":
            outdoorPWM.ChangeDutyCycle(sensors["outdoor_light"]["intensity"])
        else:
            outdoorPWM.ChangeDutyCycle(0)

        if ((prev_state != sensors["outdoor_light"]["active"] or prev_intensity != sensors["outdoor_light"]["intensity"])
                and is_connected):
            if prev_state != sensors["outdoor_light"]["active"]:
                if sensors["outdoor_light"]["active"] == "On":
                    json_dict = {"state": sensors["outdoor_light"]["active"],
                                 "intensity": sensors["outdoor_light"]["intensity"],
                                 "date": datetime.now().isoformat()}
                    client_rp.publish(TELEMETRY_TOPIC + "outdoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                    prev_intensity = sensors["outdoor_light"]["intensity"]
                else:
                    json_dict = {"state": sensors["outdoor_light"]["active"],
                                 "intensity": 0,
                                 "date": datetime.now().isoformat()}
                    client_rp.publish(TELEMETRY_TOPIC + "outdoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                    prev_intensity = 0
            else:
                json_dict = {"state": sensors["outdoor_light"]["active"],
                             "intensity": sensors["outdoor_light"]["intensity"],
                             "date": datetime.now().isoformat()}
                client_rp.publish(TELEMETRY_TOPIC + "outdoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
                prev_intensity = sensors["outdoor_light"]["intensity"]
            print("Outdoor light data sent to digital twin")
            prev_state = sensors["outdoor_light"]["active"]

        if kill:
            sem.release()
            break
        sem.release()
        time.sleep(1)

    print("[-] Finish the thread for:", name)


def button(name):
    print("[+] Create the thread for:", name)
    global kill, sem, client_rp, is_connected, sensors

    while True:
        sem.acquire()
        if not GPIO.input(buttonPin):
            sensors["presence"]["detected"] = not sensors["presence"]["detected"]
            if is_connected:
                json_dict = {"detected": 1 if sensors["presence"]["detected"] else 0, "date": datetime.now().isoformat()}
                client_rp.publish(TELEMETRY_TOPIC + "presence", payload=json.dumps(json_dict), qos=0, retain=False)
                print("Presence data sent to digital twin")
            print("Button pressed - Presence detected" if sensors["presence"]["detected"] else "Button pressed - No presence")
            sem.release()
            time.sleep(1)
            continue

        if kill:
            sem.release()
            break
        sem.release()

    print("[-] Finish the thread for:", name)


def speed(name):
    print("[+] Create the thread for:", name)
    global kill, sem, sensors, automatic

    while True:
        sem.acquire()
        if automatic:
            if sensors["presence"]["detected"]:
                if 21.0 <= sensors["temperature"]["level"] <= 24.0:
                    sensors["air-conditioner"]["level"] = 0
                    sensors["air-conditioner"]["state"] = "Stop"
                elif sensors["temperature"]["level"] < 21.0:
                    sensors["air-conditioner"]["level"] = min(int((21.0 - sensors["temperature"]["level"]) * 10), 100)
                    sensors["air-conditioner"]["state"] = "Heating"
                elif sensors["temperature"]["level"] > 24.0:
                    sensors["air-conditioner"]["level"] = min(int((sensors["temperature"]["level"] - 24.0) * 10), 100)
                    sensors["air-conditioner"]["state"] = "Cooling"
            else:
                sensors["air-conditioner"]["level"] = 0
                sensors["air-conditioner"]["state"] = "Stop"
        else:
            if sensors["air-conditioner"]["state"] == "Stop":
                sensors["air-conditioner"]["level"] = 0

        if kill:
            sem.release()
            break
        sem.release()

        time.sleep(1)

    print("[-] Finish the thread for:", name)


def motorThread(name):
    print("[+] Create the thread for:", name)
    global kill, pwm, client_rp, is_connected, sensors, sem

    prev_presence = 0
    prev_speed = 0
    prev_state = "Stop"
    while True:
        sem.acquire()
        if sensors["air-conditioner"]["level"] == 0:
            GPIO.output(Motor1E, GPIO.LOW)
        else:
            pwm.ChangeDutyCycle(sensors["air-conditioner"]["level"])
            GPIO.output(Motor1B, GPIO.LOW)
            GPIO.output(Motor1E, GPIO.HIGH)

        if ((prev_presence != sensors["presence"]["detected"] or prev_speed != sensors["air-conditioner"]["level"] or
             prev_state != sensors["air-conditioner"]["state"]) and is_connected):
            if not sensors["presence"]["detected"] or sensors["air-conditioner"]["state"] == "Stop":
                state = "Stop"
            elif sensors["air-conditioner"]["state"] == "Cooling":
                state = "Cooling"
            else:
                state = "Heating"
            json_dict = {"state": state, "value": sensors["air-conditioner"]["level"], "date": datetime.now().isoformat()}
            client_rp.publish(TELEMETRY_TOPIC + "air-conditioner", payload=json.dumps(json_dict), qos=0, retain=False)
            print("Motor data sent to digital twin")
            prev_speed = sensors["air-conditioner"]["level"]
            prev_state = sensors["air-conditioner"]["state"]
            prev_presence = sensors["presence"]["detected"]

        if kill:
            sem.release()
            break
        sem.release()

        time.sleep(1)

    print("[-] Finish the thread for:", name)


def servomotorThread(name):
    print("[+] Create the thread for:", name)
    global kill, servoPWM, client_rp, is_connected, sensors, sem

    prev_degree = 0
    while True:
        sem.acquire()
        if prev_degree != sensors["blinds"]["degree"]:
            servoPWM.ChangeDutyCycle(2 + (sensors["blinds"]["degree"] / 18))
            time.sleep(0.5)
            servoPWM.ChangeDutyCycle(0)

        if prev_degree != sensors["blinds"]["degree"] and is_connected:
            json_dict = {"degree": sensors["blinds"]["degree"],
                         "date": datetime.now().isoformat()}
            client_rp.publish(TELEMETRY_TOPIC + "blinds", payload=json.dumps(json_dict), qos=0, retain=False)
            print("Servomotor data sent to digital twin")
            prev_degree = sensors["blinds"]["degree"]

        if kill:
            sem.release()
            break
        sem.release()

        time.sleep(1)

    print("[-] Finish the thread for:", name)


def weatherSensor(name):
    print("[+] Create the thread for:", name)
    global kill, is_connected, client_rp, sensors, sem
    dht_sensor = Adafruit_DHT.DHT11
    dht_pin = 4

    prev_humid = 0
    while True:
        # Get data
        sem.acquire()
        today = date.today()
        now = datetime.now().time()
        humid, temp = Adafruit_DHT.read(dht_sensor, dht_pin)

        if humid is not None and temp is not None:
            dif_temp = abs(temp - sensors["temperature"]["level"])
            dif_humid = abs(humid - prev_humid)

            if dif_temp > 0.1 or dif_humid > 0.1:
                sensors["temperature"]["level"] = temp
                prev_humid = humid
                print(f"Temperature= {temp:0.2f}ºC\nHumidity= {humid:0.2f}%")
                if dif_temp > 0.1 and is_connected:
                    json_dict = {"value": temp, "date": datetime.now().isoformat()}
                    client_rp.publish(TELEMETRY_TOPIC + "temperature", payload=json.dumps(json_dict), qos=0, retain=False)
                    print("Temperature value sent to digital twin")
        else:
            print("Sensor failure check writing")

        if kill:
            sem.release()
            break
        sem.release()
        time.sleep(3)

    print("[-] Finish the thread for:", name)


def destroy():
    GPIO.cleanup()


def on_connect(client, userdata, flags, rc):
    global CONFIG_TOPIC
    if rc == 0:
        print("Send room ID to the digital twin")
        client_rp.publish(CONFIG_TOPIC, payload="Room-2", qos=0, retain=False)
        print("Sent ID Room-2 to topic", CONFIG_TOPIC)
        client_rp.subscribe(CONFIG_TOPIC + "/room")
        print("Subscribed to", CONFIG_TOPIC + "/room")
    else:
        print("Error connecting. Retry connection")


def send_status():
    global client_rp, sensors
    json_dict = {"value": sensors["temperature"]["level"], "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "temperature", payload=json.dumps(json_dict), qos=0, retain=False)
    json_dict = {"state": sensors["air-conditioner"]["state"], "value": sensors["air-conditioner"]["level"],
                 "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "air-conditioner", payload=json.dumps(json_dict), qos=0, retain=False)
    json_dict = {"detected": sensors["presence"]["detected"], "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "presence", payload=json.dumps(json_dict), qos=0, retain=False)
    json_dict = {"state": sensors["indoor_light"]["active"], "intensity": sensors["indoor_light"]["intensity"],
                 "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "indoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
    json_dict = {"state": sensors["outdoor_light"]["active"], "intensity": sensors["outdoor_light"]["intensity"],
                 "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "outdoor_light", payload=json.dumps(json_dict), qos=0, retain=False)
    json_dict = {"degree": sensors["blinds"]["degree"], "date": datetime.now().isoformat()}
    client_rp.publish(TELEMETRY_TOPIC + "blinds", payload=json.dumps(json_dict), qos=0, retain=False)


def on_message(client, userdata, msg):
    global is_connected, COMMAND_TOPIC, TELEMETRY_TOPIC, sensors, automatic
    topic = msg.topic.split("/")
    if "config" in topic:
        room_number = msg.payload.decode()
        is_connected = True
        print("We have established the connection with digital twin for", room_number)
        connection_topic = "/hotel/p_rooms/Room-2/connection"
        date_r = datetime.now().isoformat()
        json_data = {"room": "Room-2", "type": "physical", "date": date_r, "state": "Active"}
        client.publish(connection_topic, payload=json.dumps(json_data), qos=0, retain=False)
        print("Send connection state to digital twin")
        send_status()
        print("Status of raspberry sent to digital twin")
        client_rp.subscribe(COMMAND_TOPIC + "+")
    elif "command" in topic:
        if topic[-1] == "air_conditioner":
            data = json.loads(msg.payload.decode())
            if data["state"] == "Auto":
                automatic = True
            else:
                automatic = False
            sensors["air-conditioner"]["state"] = data["state"]
            print("Command received for air conditioner")
        elif topic[-1] == "indoor_light_state":
            data = json.loads(msg.payload.decode())
            sensors["indoor_light"]["active"] = data["state"]
            print("Command received for indoor light state", data["state"])
        elif topic[-1] == "indoor_light_value":
            data = json.loads(msg.payload.decode())
            sensors["indoor_light"]["intensity"] = int(data["value"])
            print("Command received for indoor light value", data["value"])
        elif topic[-1] == "outdoor_light_state":
            data = json.loads(msg.payload.decode())
            sensors["outdoor_light"]["active"] = data["state"]
            print("Command received for outdoor light state", data["state"])
        elif topic[-1] == "outdoor_light_value":
            data = json.loads(msg.payload.decode())
            sensors["outdoor_light"]["intensity"] = int(data["value"])
            print("Command received for outdoor light value", data["value"])
        elif topic[-1] == "blinds":
            data = json.loads(msg.payload.decode())
            sensors["blinds"]["degree"] = float(data["value"])
            print("Command received for blinds degree", sensors["blinds"]["degree"])


def do_connection():
    global client_rp
    print("Set MQTT user and password for connection")
    client_rp.username_pw_set(username="dso_server", password="dso_password")
    print("Set on connect, on message and on publish handlers")
    client_rp.on_connect = on_connect
    client_rp.on_message = on_message
    print("Set last will")
    date_r = datetime.now().isoformat()
    json_data = {"room": "Room-2", "type": "physical", "date": date_r, "state": "Inactive"}
    connection_topic = "/hotel/p_rooms/Room-2/connection"
    client_rp.will_set(connection_topic, payload=json.dumps(json_data), qos=0, retain=False)
    print("Try connection")
    client_rp.connect(MQTT_server, MQTT_port, 60)

    client_rp.loop_forever()


if __name__ == "__main__":
    setup()
    client_rp = mqtt.Client()
    try:
        mqtt_thread = threading.Thread(target=do_connection)
        button_thread = threading.Thread(target=button, args=["button"])
        dht_thread = threading.Thread(target=weatherSensor, args=["dht11 sensor"])
        motor_thread = threading.Thread(target=motorThread, args=["motor"])
        led_thread = threading.Thread(target=ledThread, args=["led"])
        speed_thread = threading.Thread(target=speed, args=["speed"])
        indoor_thread = threading.Thread(target=indoorLed, args=["indoor_light"])
        outdoor_thread = threading.Thread(target=outdoorLed, args=["outdoor_light"])
        blind_thread = threading.Thread(target=servomotorThread, args=["blinds"])

        mqtt_thread.setDaemon(True)
        mqtt_thread.start()
        button_thread.start()
        dht_thread.start()
        speed_thread.start()
        motor_thread.start()
        led_thread.start()
        indoor_thread.start()
        outdoor_thread.start()
        blind_thread.start()

        mqtt_thread.join()
        button_thread.join()
        dht_thread.join()
        speed_thread.join()
        motor_thread.join()
        led_thread.join()
        indoor_thread.join()
        outdoor_thread.join()
        blind_thread.join()

    except KeyboardInterrupt:
        kill = True
        button_thread.join()
        dht_thread.join()
        speed_thread.join()
        motor_thread.join()
        led_thread.join()
        indoor_thread.join()
        outdoor_thread.join()
        blind_thread.join()
        destroy()
