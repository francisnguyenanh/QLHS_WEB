import sqlite3

def connect_db():
    try:
        conn = sqlite3.connect('schoolX.db')
        #print("Successfully connected to school.db")  # Kiểm tra kết nối thành công
        return conn
    except sqlite3.Error as e:
        #print(f"Failed to connect to school.db: {e}")  # In lỗi nếu kết nối thất bại
        return None

def create_record(table_name, data):
    try:
        conn = connect_db()
        if conn is None:
            #print("Connection is None, cannot create record")
            return None
        cursor = conn.cursor()
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(data.values()))
        conn.commit()
        #print(f"Record created in {table_name}, lastrowid: {cursor.lastrowid}")
        return cursor.lastrowid
    except sqlite3.Error as e:
        #print(f"Error creating record in {table_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after create_record")

def read_all_records(table_name, fields=['*'], condition="is_deleted = 0"):
    try:
        conn = connect_db()
        if conn is None:
            print("Connection is None, cannot read records")
            return None
        cursor = conn.cursor()
        columns = ', '.join(fields)
        sql = f"SELECT {columns} FROM {table_name} WHERE {condition}"
        cursor.execute(sql)
        records = cursor.fetchall()
        print(sql)
        print(f"Read {len(records)} records from {table_name}")
        return records
    except sqlite3.Error as e:
        print(f"Error reading records from {table_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after read_all_records")

def read_record_by_id(table_name, record_id, fields=['*'], id_column='id'):
    try:
        conn = connect_db()
        if conn is None:
            #print("Connection is None, cannot read record by ID")
            return None
        cursor = conn.cursor()
        columns = ', '.join(fields)
        sql = f"SELECT {columns} FROM {table_name} WHERE {id_column} = ? AND is_deleted = 0"
        cursor.execute(sql, (record_id,))
        result = cursor.fetchone()
        #print(f"Read record from {table_name} with {id_column}={record_id}: {result}")
        return result
    except sqlite3.Error as e:
        #print(f"Error reading record from {table_name} with {id_column}={record_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after read_record_by_id")

def update_record(table_name, record_id, data, id_column='id'):
    try:
        conn = connect_db()
        if conn is None:
            #print("Connection is None, cannot update record")
            return False
        cursor = conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = ? AND is_deleted = 0"
        cursor.execute(sql, list(data.values()) + [record_id])
        conn.commit()
        #print(f"Updated {cursor.rowcount} record(s) in {table_name} with {id_column}={record_id}")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        #print(f"Error updating record in {table_name}: {e}")
        return False
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after update_record")

def delete_record(table_name, record_id, id_column='id'):
    try:
        conn = connect_db()
        if conn is None:
            #print("Connection is None, cannot delete record")
            return False
        cursor = conn.cursor()
        sql = f"DELETE FROM {table_name} WHERE {id_column} = ?"
        #sql = f"UPDATE {table_name} SET is_deleted = 1 WHERE {id_column} = ? AND is_deleted = 0"
        cursor.execute(sql, (record_id,))
        conn.commit()
        #print(f"Deleted {cursor.rowcount} record(s) in {table_name} with {id_column}={record_id}")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        #print(f"Error deleting record in {table_name}: {e}")
        return False
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after delete_record")

def get_records_by_date_range(table_name, start_date, end_date, conditions=None, fields=['*']):
    try:
        conn = connect_db()
        if conn is None:
            #print("Connection is None, cannot get records by date range")
            return None
        cursor = conn.cursor()
        columns = ', '.join(fields)
        sql = f"SELECT {columns} FROM {table_name} WHERE registered_date BETWEEN ? AND ? AND is_deleted = 0"
        params = [start_date, end_date]

        if conditions:
            for key, value in conditions.items():
                if value is not None:
                    sql += f" AND {key} = ?"
                    params.append(value)

        cursor.execute(sql, params)
        records = cursor.fetchall()
        #print(f"Read {len(records)} records from {table_name} between {start_date} and {end_date}")
        return records
    except sqlite3.Error as e:
        #print(f"Error getting records from {table_name} by date range: {e}")
        return None
    finally:
        if conn:
            conn.close()
            #print("Database connection closed after get_records_by_date_range")