FROM python:3.7.3

COPY /app /etc/usr/src/app

WORKDIR /etc/usr/src/app

# install any needed packages
RUN pip install mysql-connector-python Flask Flask-Cors

# run python script when the container launches
ENTRYPOINT ["python"]
CMD ["data_ingestion_api_rest.py"]