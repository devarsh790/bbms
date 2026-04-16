import MySQLdb
import sys

# Config from app.py
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'bloodbank' # Expected DB name from config

# Database creation logic
try:
    print(f"Connecting to MySQL server at {MYSQL_HOST} with user {MYSQL_USER}...")
    # Connect without selecting DB first
    conn = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD)
    cursor = conn.cursor()
    
    # Create Database if it doesn't exist
    print(f"Creating database '{MYSQL_DB}' if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
    conn.commit()
    
    # Select the database
    conn.select_db(MYSQL_DB)
    
    # Create Tables
    tables = [
        """CREATE TABLE IF NOT EXISTS RECEPTION(
            E_ID VARCHAR(54) PRIMARY KEY,
            NAME VARCHAR(100),
            EMAIL VARCHAR(100),
            PASSWORD VARCHAR(100),
            REGISTER_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS DONOR(
            D_ID INT(3) NOT NULL AUTO_INCREMENT,
            DNAME VARCHAR(50),
            SEX VARCHAR(10),
            AGE INT(3),
            WEIGHT INT(3),
            ADDRESS VARCHAR(150),
            DISEASE VARCHAR(50),
            DEMAIL VARCHAR(100),
            DONOR_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(D_ID)
        );""",
        """CREATE TABLE IF NOT EXISTS BLOODBANK(
            B_GROUP VARCHAR(4),
            TOTAL_PACKETS INT(4),
            PRIMARY KEY(B_GROUP)
        );""",
        """CREATE TABLE IF NOT EXISTS BLOOD(
            B_CODE INT(4) NOT NULL AUTO_INCREMENT,
            D_ID INT(3),
            B_GROUP VARCHAR(4),
            PACKETS INT(2),
            PRIMARY KEY(B_CODE),
            FOREIGN KEY(D_ID) REFERENCES DONOR(D_ID) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(B_GROUP) REFERENCES BLOODBANK(B_GROUP) ON DELETE CASCADE ON UPDATE CASCADE
        );""",
        """CREATE TABLE IF NOT EXISTS CONTACT(
            CONTACT_ID INT(3) NOT NULL AUTO_INCREMENT,
            B_GROUP VARCHAR(4),
            C_PACKETS INT(2),
            F_NAME VARCHAR(50),
            ADRESS VARCHAR(250),
            PRIMARY KEY(CONTACT_ID),
            FOREIGN KEY(B_GROUP) REFERENCES BLOODBANK(B_GROUP) ON DELETE CASCADE ON UPDATE CASCADE
        )ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=latin1;""",
        """CREATE TABLE IF NOT EXISTS NOTIFICATIONS(
            N_ID INT(3) NOT NULL AUTO_INCREMENT,
            NB_GROUP VARCHAR(4),
            N_PACKETS INT(2),
            NF_NAME VARCHAR(50),
            NADRESS VARCHAR(250),
            PRIMARY KEY(N_ID)
        )ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=latin1;"""
    ]
    
    for table_sql in tables:
        try:
            cursor.execute(table_sql)
            print("Table created successfully.")
        except MySQLdb.Error as e:
            print(f"Error creating table: {e}")

    # Trigger
    # Different MySQL versions handle triggers slightly differently via python connectors
    # We'll rely on the standard syntax.
    try:
        cursor.execute("DROP TRIGGER IF EXISTS agecheck")
        cursor.execute("""
            CREATE TRIGGER agecheck BEFORE INSERT ON DONOR FOR EACH ROW 
            BEGIN
                IF NEW.age < 21 THEN SET NEW.age = 0; END IF;
            END
        """)
        print("Trigger 'agecheck' created.")
    except MySQLdb.Error as e:
        print(f"Error creating trigger: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database setup completed successfully.")

except MySQLdb.Error as e:
    print(f"Error connecting to MySQL: {e}")
    print("Please ensure MySQL is running and accessible with the credentials specified in setup_db.py")
    sys.exit(1)
