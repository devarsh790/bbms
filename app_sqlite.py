from flask import Flask, render_template, flash, redirect, request, url_for, session, logging
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
from flask_mail import Mail, Message
import random
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key='some secret key'

# Email Configuration Setup
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your_email@gmail.com' # Replace with your email
app.config['MAIL_PASSWORD'] = 'your_app_password' # Replace with your App Password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

DB_NAME = 'bloodbank.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DB_NAME):
        conn = get_db_connection()
        with app.open_resource('schema.sql') as f:
            conn.executescript(f.read().decode('utf8'))
        conn.close()

# Mock MySQL object to minimize code changes structure-wise, 
# but actually we will replace cursor usage.
# Instead of rewriting everything to use `get_db_connection` context managers everywhere, 
# let's create a helper class that mimics `mysql.connection.cursor()` behavior but for sqlite.

class SQLiteConnection:
    def cursor(self):
        self.conn = get_db_connection()
        return SQLiteCursor(self.conn)
    
    def commit(self):
        # In this design, commit is handled by the connection, 
        # but we need to ensure the cursor's connection is the one committed.
        # This wrapper is a bit leaky if not careful.
        # Better approach: Modify the route handlers to use sqlite patterns.
        pass

# We will modify the routes directly to use get_db_connection()
# It's cleaner than building a compatibility layer.

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        bgroup = request.form["bgroup"]
        bpackets = request.form["bpackets"]
        fname = request.form["fname"]
        adress = request.form["adress"]

        conn = get_db_connection()
        cur = conn.cursor()
        
        #Inserting values into tables
        cur.execute("INSERT INTO CONTACT(B_GROUP,C_PACKETS,F_NAME,ADRESS) VALUES(?, ?, ?, ?)",(bgroup, bpackets, fname, adress))
        cur.execute("INSERT INTO NOTIFICATIONS(NB_GROUP,N_PACKETS,NF_NAME,NADRESS) VALUES(?, ?, ?, ?)",(bgroup, bpackets, fname, adress))
        
        conn.commit()
        conn.close()
        
        flash('Your request is successfully sent to the Blood Bank','success')
        return redirect(url_for('index'))

    return render_template('contact.html')


class RegisterForm(Form):
    name = StringField('Name', [validators.DataRequired(),validators.Length(min=1,max=25)])
    email = StringField('Email',[validators.DataRequired(),validators.Length(min=10,max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method  == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        e_id = name+str(random.randint(1111,9999))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("INSERT INTO RECEPTION(E_ID,NAME,EMAIL,PASSWORD) VALUES(?, ?, ?, ?)",(e_id, name, email, password))
        
        conn.commit()
        conn.close()
        
        # Send Welcome Email
        try:
            msg = Message('Welcome to Blood Bank Management', sender=app.config.get('MAIL_USERNAME'), recipients=[email])
            msg.body = f"Hello {name},\n\nThank you for registering. Your associated Staff/Donor ID is: {e_id}\n\nPlease keep this ID safe for future logins."
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
            
        flashing_message = "Success! You can log in with your Email"
        flash( flashing_message,"success")

        return redirect(url_for('login'))

    return render_template('register.html',form = form)

#login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        email = request.form["email"]
        password_candidate = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        # Get user by email
        cur.execute("SELECT * FROM RECEPTION WHERE EMAIL = ?", [email])
        data = cur.fetchone()

        if data:
            password = data['PASSWORD']
            e_id = data['E_ID']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['e_id'] = e_id

                # Send Login Alert Email
                try:
                    msg = Message('New Login Alert', sender=app.config.get('MAIL_USERNAME'), recipients=[email])
                    msg.body = f"Hello,\n\nA new login was detected on your account. Your Staff/Donor ID is: {e_id}.\nIf this wasn't you, please contact administration."
                    mail.send(msg)
                except Exception as e:
                    print(f"Failed to send login alert email: {e}")

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            
            cur.close() # Actually conn.close()
            conn.close()
        else:
            conn.close()
            error = 'Email not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login!', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Simulate stored procedure or just run query
    # Original used: cur.callproc('BLOOD_DATA')
    # We will just run the query that BLOOD_DATA likely does.
    # Assuming it gets all blood info.
    
    # Creating a replacement for the stored procedure
    # Let's assume BLOOD_DATA selects from BLOOD or BLOODBANK
    # If we look at other routes, updating BLOODBANK.
    
    # Query BLOODBANK but sort by blood groups that have requests in the CONTACT table first
    query = """
    SELECT b.B_GROUP, b.TOTAL_PACKETS, COUNT(c.CONTACT_ID) as REQUEST_COUNT
    FROM BLOODBANK b
    LEFT JOIN CONTACT c ON b.B_GROUP = c.B_GROUP
    GROUP BY b.B_GROUP, b.TOTAL_PACKETS
    ORDER BY REQUEST_COUNT DESC, b.B_GROUP ASC
    """
    cur.execute(query)
    details = cur.fetchall()

    cur.execute("SELECT * FROM APPOINTMENTS ORDER BY ADATE ASC, ATIME ASC")
    appointments = cur.fetchall()

    if details:
        return render_template('dashboard.html',details=details, appointments=appointments)
    else:
        msg = ' Blood Bank is Empty '
        return render_template('dashboard.html',msg=msg, appointments=appointments)
    
    conn.close()

@app.route('/donate', methods=['GET', 'POST'])
@is_logged_in
def donate():
    if request.method  == 'POST':
        # Get Form Fields
        dname = request.form["dname"]
        b_group = request.form["b_group"]
        sex = request.form["sex"]
        age = request.form["age"]
        weight = request.form["weight"]
        address = request.form["address"]
        disease =  request.form["disease"]
        demail = request.form["demail"]

        conn = get_db_connection()
        cur = conn.cursor()

        #Inserting values into tables
        cur.execute("INSERT INTO DONOR(DNAME,B_GROUP,SEX,AGE,WEIGHT,ADDRESS,DISEASE,DEMAIL) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",(dname, b_group, sex, age, weight, address, disease, demail))
        
        conn.commit()
        conn.close()
        
        flash('Success! Donor details Added.','success')
        return redirect(url_for('donorlogs'))

    return render_template('donate.html')

@app.route('/donorlogs')
@is_logged_in
def donorlogs():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM DONOR")
    logs = cur.fetchall()

    if logs:
        return render_template('donorlogs.html',logs=logs)
    else:
        msg = ' No logs found '
        return render_template('donorlogs.html',msg=msg)
    
    conn.close()


@app.route('/bloodform',methods=['GET','POST'])
@is_logged_in
def bloodform():
    if request.method  == 'POST':
        # Get Form Fields
        d_id = request.form["d_id"]
        blood_group = request.form["blood_group"]
        packets = request.form["packets"]

        conn = get_db_connection()
        cur = conn.cursor()

        #Inserting values into tables
        cur.execute("INSERT INTO BLOOD(D_ID,B_GROUP,PACKETS) VALUES(?, ?, ?)",(d_id , blood_group, packets))
        
        # Check if row exists in BLOODBANK first
        cur.execute("SELECT * FROM BLOODBANK WHERE B_GROUP = ?", (blood_group,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS + ? WHERE B_GROUP = ?",(packets,blood_group))
        else:
             # Just in case, though foreign keys might fail if strict.
             # But let's assume valid blood group.
             pass

        conn.commit()
        conn.close()
        
        flash('Success! Donor Blood details Added.','success')
        return redirect(url_for('dashboard'))

    return render_template('bloodform.html')


@app.route('/notifications')
@is_logged_in
def notifications():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM CONTACT")
    requests = cur.fetchall()

    if requests:
        return render_template('notification.html',requests=requests)
    else:
        msg = ' No requests found '
        return render_template('notification.html',msg=msg)
    
    conn.close()

@app.route('/notifications/accept/<int:id>')
@is_logged_in
def accept(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # First get the details of the request to deduct from BLOODBANK
    cur.execute("SELECT B_GROUP, C_PACKETS FROM CONTACT WHERE CONTACT_ID = ?", (id,))
    req = cur.fetchone()
    if req:
        # Deduct the requested packets from inventory
        cur.execute("UPDATE BLOODBANK SET TOTAL_PACKETS = TOTAL_PACKETS - ? WHERE B_GROUP = ?", (req['C_PACKETS'], req['B_GROUP']))
        
        # Then remove the request
        cur.execute("DELETE FROM CONTACT WHERE CONTACT_ID = ?", (id,))
        conn.commit()
        flash('Request Accepted and removed from inventory logs','success')
    else:
        flash('Request not found','danger')
        
    conn.close()
    return redirect(url_for('notifications'))

@app.route('/notifications/decline/<int:id>')
@is_logged_in
def decline(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM CONTACT WHERE CONTACT_ID = ?", (id,))
    conn.commit()
    conn.close()
    flash('Request Declined and removed from logs','danger')
    return redirect(url_for('notifications'))

# New Pages Routes
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/process')
def process():
    return render_template('process.html')

@app.route('/statistics')
@is_logged_in
def statistics():
    return render_template('statistics.html')

@app.route('/emergency')
def emergency():
    return render_template('emergency.html')

@app.route('/stories')
def stories():
    return render_template('stories.html')

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if request.method == 'POST':
        # Handle appointment booking
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        blood_type = request.form.get("blood_type")
        adate = request.form.get("date")
        atime = request.form.get("time")
        location = request.form.get("location")
        donation_type = request.form.get("donation_type")
        notes = request.form.get("notes", "")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO APPOINTMENTS(NAME, EMAIL, PHONE, BLOOD_TYPE, ADATE, ATIME, LOCATION, DONATION_TYPE, NOTES) 
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, email, phone, blood_type, adate, atime, location, donation_type, notes))
        
        conn.commit()
        conn.close()

        flash('Appointment request received! We will contact you shortly.', 'success')
        return redirect(url_for('appointments'))
    return render_template('appointments.html')

@app.route('/compatibility')
def compatibility():
    return render_template('compatibility.html')

# Database Initialization Script embedded
def setup_database():
    print("Initializing SQLite database...")
    conn = get_db_connection()
    
    # Schema creation
    schema = [
        """CREATE TABLE IF NOT EXISTS RECEPTION(
            E_ID VARCHAR(54) PRIMARY KEY,
            NAME VARCHAR(100),
            EMAIL VARCHAR(100),
            PASSWORD VARCHAR(100),
            REGISTER_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS DONOR(
            D_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            DNAME VARCHAR(50),
            B_GROUP VARCHAR(4),
            SEX VARCHAR(10),
            AGE INTEGER,
            WEIGHT INTEGER,
            ADDRESS VARCHAR(150),
            DISEASE VARCHAR(50),
            DEMAIL VARCHAR(100),
            DONOR_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS BLOODBANK(
            B_GROUP VARCHAR(4) PRIMARY KEY,
            TOTAL_PACKETS INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS BLOOD(
            B_CODE INTEGER PRIMARY KEY AUTOINCREMENT,
            D_ID INTEGER,
            B_GROUP VARCHAR(4),
            PACKETS INTEGER,
            FOREIGN KEY(D_ID) REFERENCES DONOR(D_ID) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY(B_GROUP) REFERENCES BLOODBANK(B_GROUP) ON DELETE CASCADE ON UPDATE CASCADE
        );""",
        """CREATE TABLE IF NOT EXISTS CONTACT(
            CONTACT_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            B_GROUP VARCHAR(4),
            C_PACKETS INTEGER,
            F_NAME VARCHAR(50),
            ADRESS VARCHAR(250),
            FOREIGN KEY(B_GROUP) REFERENCES BLOODBANK(B_GROUP) ON DELETE CASCADE ON UPDATE CASCADE
        );""",
        """CREATE TABLE IF NOT EXISTS NOTIFICATIONS(
            N_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            NB_GROUP VARCHAR(4),
            N_PACKETS INTEGER,
            NF_NAME VARCHAR(50),
            NADRESS VARCHAR(250)
        );"""
    ]
    
    for statement in schema:
        conn.execute(statement)
        
    # Initialize Blood Bank Groups if empty
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('A+', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('A-', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('B+', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('B-', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('AB+', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('AB-', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('O+', 0)")
    conn.execute("INSERT OR IGNORE INTO BLOODBANK (B_GROUP, TOTAL_PACKETS) VALUES ('O-', 0)")
    
    # New table for appointments
    conn.execute("""CREATE TABLE IF NOT EXISTS APPOINTMENTS(
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        NAME VARCHAR(100),
        EMAIL VARCHAR(100),
        PHONE VARCHAR(20),
        BLOOD_TYPE VARCHAR(4),
        ADATE DATE,
        ATIME VARCHAR(10),
        LOCATION VARCHAR(50),
        DONATION_TYPE VARCHAR(50),
        NOTES TEXT,
        STATUS VARCHAR(20) DEFAULT 'Pending'
    );""")

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    setup_database()
    app.run(debug=True, port=8000) # Use 8000 to avoid conflict if old app is zombie
