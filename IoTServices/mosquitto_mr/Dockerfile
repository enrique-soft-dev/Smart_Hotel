# pull debian image from docker hub
FROM debian:buster

# update and upgrade both repositories and packages
RUN apt update && apt upgrade -y

# install mqtt dependencies
RUN apt install mosquitto mosquitto-clients -y

# set provisional password
RUN touch /etc/mosquitto/passwd
RUN mosquitto_passwd -b /etc/mosquitto/passwd dso_server dso_password

# launch application
CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]