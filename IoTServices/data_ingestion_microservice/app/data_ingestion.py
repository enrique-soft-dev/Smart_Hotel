import sys
import os
import mysql.connector


def connect_database():
    mydb = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    return mydb


def insert_device_state(params):
    mydb = connect_database()
    row_count = 0
    with mydb.cursor() as my_cursor:
        sql = "INSERT INTO device_state (room, type, value, date) VALUES (%s, %s, %s, %s)"
        values = (
            params["room"],
            params["type"],
            params["value"],
            params["date"]
        )
        my_cursor.execute(sql, values)
        row_count = my_cursor.rowcount
        mydb.commit()
    mydb.close()
    return row_count


def check_connection(room, type_room):
    mydb = connect_database()
    result = False
    with mydb.cursor(buffered=True) as my_cursor:
        sql = "select * from connections where room=%s and type=%s"
        values = (
            room,
            type_room
        )
        my_cursor.execute(sql, values)
        record = my_cursor.fetchall()
        if len(record) != 0:
            result = True
    mydb.close()
    return result


def update_connection(params):
    mydb = connect_database()
    row_count = 0
    with mydb.cursor() as my_cursor:
        sql = "UPDATE connections SET state=%s, date=%s WHERE room=%s AND type=%s"
        values = (
            params["value"],
            params["date"],
            params["room"],
            params["type"]
        )
        my_cursor.execute(sql, values)
        row_count = my_cursor.rowcount
        mydb.commit()
    mydb.close()
    return row_count


def insert_connection(params):
    mydb = connect_database()
    row_count = 0
    with mydb.cursor() as my_cursor:
        sql = "INSERT INTO connections (room, type, state, date) VALUES (%s, %s, %s, %s)"
        values = (
            params["room"],
            params["type"],
            params["value"],
            params["date"]
        )
        my_cursor.execute(sql, values)
        row_count = my_cursor.rowcount
        mydb.commit()
    mydb.close()
    return row_count


def get_devices_states(room):
    mydb = connect_database()
    data = []
    with mydb.cursor(buffered=True) as my_cursor:
        sql_t = "select * from device_state where room='{0}' and type='temperature' order by date desc limit 2".format(room)
        my_cursor.execute(sql_t)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "temperature", "value": record[0][3]})
        sql_p = "select * from device_state where room='{0}' and type='presence' order by date desc limit 2".format(room)
        my_cursor.execute(sql_p)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "presence", "value": record[0][3]})
        sql_as = "select * from device_state where room='{0}' and type='air-state' order by date desc limit 2".format(room)
        my_cursor.execute(sql_as)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "air-mode", "value": record[0][3]})
        sql_al = "select * from device_state where room='{0}' and type='air-level' order by date desc limit 2".format(room)
        my_cursor.execute(sql_al)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "air-level", "value": record[0][3]})
        sql_is = "select * from device_state where room='{0}' and type='indoor-state' order by date desc limit 2".format(room)
        my_cursor.execute(sql_is)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "indoor-mode", "value": record[0][3]})
        sql_il = "select * from device_state where room='{0}' and type='indoor-value' order by date desc limit 2".format(room)
        my_cursor.execute(sql_il)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "indoor-level", "value": record[0][3]})
        sql_os = "select * from device_state where room='{0}' and type='outdoor-state' order by date desc limit 2".format(room)
        my_cursor.execute(sql_os)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "outdoor-mode", "value": record[0][3]})
        sql_ol = "select * from device_state where room='{0}' and type='outdoor-value' order by date desc limit 2".format(room)
        my_cursor.execute(sql_ol)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "outdoor-level", "value": record[0][3]})
        sql_b = "select * from device_state where room='{0}' and type='blind-degree' order by date desc limit 2".format(room)
        my_cursor.execute(sql_b)
        record = my_cursor.fetchall()
        data.append({"room": room, "type": "blind", "value": record[0][3]})

    mydb.close()
    return data
