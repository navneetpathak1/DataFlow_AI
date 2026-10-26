"""
Database utilities
Handles the connection and execution of SQL queries.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseUtil:

    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None
        self.get_connection()

    def get_connection(self):
        if self.connection is None or getattr(self.connection, "closed", 1):
            try:
                self.connection = psycopg2.connect(**self.db_config)
            except Exception as e:
                print(f"Error connecting to the database: {e}")
                self.connection = None
        return self.connection

    # returns schema details of the database including tables, columns, data types and sample data
    def schema_details(self, schema_name):

        schema_info_context = f"Database Schema: {schema_name}\n"
        connection = self.get_connection()
        if not connection:
            return f"Error: Unable to connect to database using config {self.db_config}"

        cursor = None
        try:
            cursor = connection.cursor()

            cursor.execute("SELECT table_name from information_schema.tables where table_schema = %s;", (schema_name,))
            tables_list = cursor.fetchall()

            for table in tables_list:
                table_name = table[0]
                schema_info_context = f"{schema_info_context}\nTable: {table_name}\n"

                # Adding Columns & Data Types
                cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;", (table_name,))
                columns_list = cursor.fetchall()

                for column in columns_list:
                    column_name = column[0]
                    data_type = column[1]
                    schema_info_context = f"{schema_info_context}  Column: {column_name}, Data Type: {data_type}\n"

                # Adding Sample Data (max 5 rows)
                cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                sample_data = cursor.fetchall()
                schema_info_context = f"{schema_info_context}  Sample Data:\n"
                for row in sample_data:
                    schema_info_context = f"{schema_info_context}    {row}\n"

        except Exception as e:
            print(f"Error fetching schema details: {e}")
            schema_info_context = f"Error fetching schema details: {e}"

        finally:
            if cursor:
                cursor.close()

        return schema_info_context

    # executes the given SQL query on the database
    def execute_sql(self, query):
        connection = self.get_connection()
        if not connection:
            return None

        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            if cursor.description:
                result = cursor.fetchall()
            else:
                result = []
            connection.commit()
            return str(result)
        except Exception as e:
            print(f"Error executing query: {e}")
            try:
                if connection and not getattr(connection, "closed", 1):
                    connection.rollback()
            except Exception:
                pass
            return None
        finally:
            if cursor:
                cursor.close()

    def close(self):
        if self.connection and not getattr(self.connection, "closed", 1):
            self.connection.close()


if __name__ == "__main__":
    obj = DatabaseUtil({
        "host": os.environ.get('host', 'localhost'),
        "port": os.environ.get('port', 5432),
        "user": os.environ.get('user', 'postgres'),
        "password": os.environ.get('password', ''),
        "dbname": os.environ.get('database', 'first')
    })

    result = obj.schema_details("public")

    with open("test_schema_details.txt", "w") as f:
        f.write(result)
