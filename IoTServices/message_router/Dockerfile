FROM python:3.7.3

COPY /app /etc/usr/src/app

WORKDIR /etc/usr/src/app

#install any needed packages specified in requirements.txt
RUN pip install paho-mqtt requests Flask Flask-Cors
# run run.oy when the container launches
ENTRYPOINT ["python"]
CMD ["message_router.py"]