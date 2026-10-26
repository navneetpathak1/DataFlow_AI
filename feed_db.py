import os
import csv
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

if 'port' not in os.environ:
    os.environ['port'] = '5432'

# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.environ['host'],
    "port": int(os.environ['port']),
    "database": os.environ['database'],
    "user": os.environ['user'],
    "password": os.environ['password'],
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(BASE_DIR, "datas", "csv")


# ============================================================
# DATABASE CONNECTION
# ============================================================

conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = False

cursor = conn.cursor()

print("Connected to PostgreSQL")


# ============================================================
# CREATE TABLES
# ============================================================

create_tables_sql = """

CREATE SCHEMA IF NOT EXISTS public;

-- =========================================================
-- STORE
-- =========================================================

CREATE TABLE IF NOT EXISTS public.store (
    store_id INT PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL UNIQUE
);


-- =========================================================
-- EMPLOYEE
-- =========================================================

CREATE TABLE IF NOT EXISTS public.employee (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100) NOT NULL,
    store_id INT NOT NULL,
    salary NUMERIC(10, 2) NOT NULL
        CHECK (salary >= 0),
    age INT NOT NULL
        CHECK (age >= 18),
    working_years INT NOT NULL
        CHECK (working_years >= 0),

    CONSTRAINT fk_employee_store
        FOREIGN KEY (store_id)
        REFERENCES public.store(store_id)
);


-- =========================================================
-- CUSTOMERS
-- =========================================================

CREATE TABLE IF NOT EXISTS public.customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    product_bought VARCHAR(150) NOT NULL,
    price NUMERIC(12, 2) NOT NULL
        CHECK (price >= 0),

    month VARCHAR(15) NOT NULL
        CHECK (
            month IN (
                'January', 'February', 'March', 'April',
                'May', 'June', 'July', 'August',
                'September', 'October', 'November', 'December'
            )
        )
);


-- =========================================================
-- SALES
-- =========================================================

CREATE TABLE IF NOT EXISTS public.sales (
    sales_id INT PRIMARY KEY,
    product VARCHAR(150) NOT NULL,
    money NUMERIC(14, 2) NOT NULL
        CHECK (money >= 0),

    month VARCHAR(15) NOT NULL
        CHECK (
            month IN (
                'January', 'February', 'March', 'April',
                'May', 'June', 'July', 'August',
                'September', 'October', 'November', 'December'
            )
        ),

    store_id INT NOT NULL,

    CONSTRAINT fk_sales_store
        FOREIGN KEY (store_id)
        REFERENCES public.store(store_id)
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_employee_store_id
ON public.employee(store_id);

CREATE INDEX IF NOT EXISTS idx_sales_store_id
ON public.sales(store_id);

CREATE INDEX IF NOT EXISTS idx_sales_month
ON public.sales(month);

CREATE INDEX IF NOT EXISTS idx_customers_month
ON public.customers(month);

"""

cursor.execute(create_tables_sql)

print("Tables created successfully")


# ============================================================
# OPTIONAL: CLEAR EXISTING DATA
# ============================================================

# Uncomment this block if you want to reload CSV data
# from scratch on every execution.

# cursor.execute("""
#     TRUNCATE TABLE
#         public.employee,
#         public.customers,
#         public.sales,
#         public.store
#     CASCADE;
# """)



# ============================================================
# LOAD CSV USING POSTGRES COPY
# ============================================================

def load_csv(table_name, csv_file, columns):

    file_path = os.path.join(CSV_DIR, csv_file)

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    copy_sql = sql.SQL("""
        COPY {} ({})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER ',',
            NULL ''
        )
    """).format(
        sql.Identifier("public", table_name),
        sql.SQL(", ").join(
            sql.Identifier(column)
            for column in columns
        )
    )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        cursor.copy_expert(
            copy_sql,
            file
        )

    print(f"Loaded {csv_file}")


# ============================================================
# LOAD STORE
# ============================================================

load_csv(
    "store",
    "Store.csv",
    [
        "store_id",
        "store_name",
    ],
)


# ============================================================
# LOAD EMPLOYEE
# ============================================================

load_csv(
    "employee",
    "Employee.csv",
    [
        "employee_id",
        "employee_name",
        "store_id",
        "salary",
        "age",
        "working_years",
    ],
)


# ============================================================
# LOAD CUSTOMERS
# ============================================================

load_csv(
    "customers",
    "Customers.csv",
    [
        "customer_id",
        "customer_name",
        "product_bought",
        "price",
        "month",
    ],
)


# ============================================================
# LOAD SALES
# ============================================================

load_csv(
    "sales",
    "Sales.csv",
    [
        "sales_id",
        "product",
        "money",
        "month",
        "store_id",
    ],
)


# ============================================================
# VERIFY RECORD COUNTS
# ============================================================

tables = [
    "store",
    "employee",
    "customers",
    "sales",
]

print("\nRecord counts:")
print("-" * 40)

for table in tables:

    cursor.execute(
        sql.SQL(
            "SELECT COUNT(*) FROM {}.{}"
        ).format(
            sql.Identifier("public"),
            sql.Identifier(table)
        )
    )

    count = cursor.fetchone()[0]

    print(f"{table:<15} {count:>10,}")


# ============================================================
# COMMIT
# ============================================================

conn.commit()

print("\nData loaded successfully!")
print("Transaction committed.")


# ============================================================
# CLOSE CONNECTION
# ============================================================

cursor.close()
conn.close()

print("PostgreSQL connection closed.")