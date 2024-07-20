from flask import Flask, render_template, request, redirect, url_for, session,flash
import mysql.connector
import os
import random
import string
import smtplib
import logging
from werkzeug.security import generate_password_hash, check_password_hash

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from werkzeug.utils import secure_filename




app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

jobs = [
    {'id': 1, 'title': 'Software Engineer', 'location': 'New York', 'industry': 'Technology'},
    {'id': 2, 'title': 'Data Scientist', 'location': 'San Francisco', 'industry': 'Technology'},
    {'id': 3, 'title': 'Project Manager', 'location': 'Chicago', 'industry': 'Business'},
    # Add more job entries as needed
]
 

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Girija@123',
        database='project'
    )
    cursor = conn.cursor()
except mysql.connector.Error as e:
    print("Error connecting to MySQL database:", e)
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = 'Hi! Welcome'
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form:
        username = request.form['name']
        password = request.form['password']

        cursor.execute('SELECT * FROM users WHERE name = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account[0]
            session['name'] = account[1]
            session['role'] = account[4]  # Assuming role is stored in the 4th column

            msg = 'Logged in successfully!'
            if session['role'] == 'employer':
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (account[0],))
                value = cursor.fetchall()
                return render_template('employer_dashboard.html', data=value)
            elif session['role'] == 'job_seeker':
                cursor.execute("SELECT * FROM jobs")
                jobs = cursor.fetchall()
                return render_template('jobseeker_dashboard.html', jobs=jobs)
        else:
            msg = 'Incorrect username / password!'
    return render_template('login.html', msg=msg)



@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form and 'role' in request.form and 'userid' in request.form:
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        userid = request.form['userid']

        cursor.execute('SELECT * FROM users WHERE user_id= %s', (userid,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not name or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO users(name,password,email,role,user_id) VALUES (%s, %s,%s,%s,%s)', (name, password, email, role, userid))
            conn.commit()
            msg = 'You have successfully registered!'
            
            # Log the user in
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (userid,))
            account = cursor.fetchone()
            session['loggedin'] = True
            session['id'] = account[0]
            session['name'] = account[1]
            session['role'] = account[4]

            # Redirect based on role
            if session['role'] == 'employer':
                cursor.execute("SELECT * FROM users WHERE user_id = %s", (account[0],))
                value = cursor.fetchall()
                return render_template('employer_dashboard.html', data=value)
            elif session['role'] == 'job_seeker':
                cursor.execute("SELECT * FROM jobs")
                jobs = cursor.fetchall()
                return render_template('jobseeker_dashboard.html', jobs=jobs)
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('name', None)
    return redirect(url_for('login'))


@app.route('/employer_dashboard')
def employer_dashboard():
    if 'loggedin' in session and session['role'] == 'employer':
        cursor.execute('SELECT * FROM jobs WHERE employer_id = %s', (session['id'],))
        jobs = cursor.fetchall()
        return render_template('employer_dashboard.html', jobs=jobs)
    return redirect(url_for('login'))

@app.route('/job_list', methods=['POST', 'GET'])
def job_list():    
    if request.method == 'POST':
        if 'loggedin' in session:
            location = request.form['location']
            desc = request.form['desc']
            user_id = session['id']
            job_title = request.form['title']
            req = request.form['req']
            industry = request.form['industry']

            try:
                cursor.execute("INSERT INTO jobs (location, description, user_id, title, requirements, industry) VALUES (%s, %s, %s, %s, %s, %s)", 
                               (location, desc, user_id, job_title, req, industry))
                conn.commit()
                return redirect(url_for('dashboard'))
            except mysql.connector.Error as e:
                print("Error executing SQL query:", e)
                return redirect(url_for('dashboard'))
            
    else:
        return render_template('jobdetails.html')
@app.route('/')
@app.route('/home')
def home():
    return render_template("jobdetails.html")

@app.route('/password_recovery', methods=['GET', 'POST'])
def password_recovery():
    msg = ''
    if request.method == 'POST' and 'email' in request.form:
        email = request.form['email']
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            cursor.execute('UPDATE users SET reset_token = %s WHERE email = %s', (token, email))
            conn.commit()
            reset_link = url_for('password_recovery', token=token, _external=True)
            send_reset_email(email, reset_link)
            msg = 'Password recovery email has been sent!'
        else:
            msg = 'No account associated with this email!'
    return render_template('password_recovery.html', msg=msg)
def send_reset_email(email, reset_link):
    try:
        sender_email = "your_email@example.com"
        sender_password = "your_email_password"
        receiver_email = email

        message = MIMEMultipart("alternative")
        message["Subject"] = "Password Reset Request"
        message["From"] = sender_email
        message["To"] = receiver_email

        text = f"Please click the link to reset your password: {reset_link}"
        part = MIMEText(text, "plain")
        message.attach(part)

        with smtplib.SMTP("smtp.yourmailserver.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        print("Password reset email sent!")
    except Exception as e:
        print("Failed to send email:", e)
@app.route('/edit', methods=['POST', 'GET'])
def edit():
    if request.method == 'POST':
        id = request.form['id']
        title = request.form['title']
        desc = request.form['desc']
        requirements = request.form['req']
        location = request.form['location']
        industry = request.form['industry']

        try:
            cursor.execute("UPDATE jobs SET title = %s, description = %s, requirements = %s, location = %s, industry = %s WHERE id = %s",
                           (title, desc, requirements, location, industry, id))
            conn.commit()
            # Explicitly redirect to employer dashboard after updating the job
            return redirect(url_for('employer_dashboard'))
        except mysql.connector.Error as e:
            print("Error updating data:", e)
            # Explicitly redirect to employer dashboard on error
            return redirect(url_for('employer_dashboard'))
    elif request.method == 'GET':
        id = request.args.get('job_id')
        if id:
            cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (id,))
            value = cursor.fetchone()
            if value:
                return render_template('edit.html', data=value)
            else:
                return "Job not found"
        else:
            return "Job ID not provided"


@app.route('/delete', methods=['GET'])
def delete():
    job_id = request.args.get('job_id')
    if job_id:
        try:
            cursor.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
            conn.commit()
            return redirect(url_for('dashboard'))
        except mysql.connector.Error as e:
            print("Error deleting data:", e)
            return redirect(url_for('dashboard'))
    else:
        return "Job ID not provided"

@app.route('/jobseeker_dashboard')
def jobseeker_dashboard():
    if 'loggedin' in session and session['role'] == 'job_seeker':
        cursor.execute("SELECT * FROM jobs")
        jobs = cursor.fetchall()
        
        # Fetch notifications for the logged-in user
        cursor.execute("SELECT * FROM notifications WHERE job_id = %s", (session['id'],))
        notifications = cursor.fetchall()
        
        # Fetch user preferences
        cursor.execute("SELECT * FROM job_preferences WHERE id = %s", (session['id'],))
        preferences = cursor.fetchone()
        
        return render_template('jobseeker_dashboard.html', jobs=jobs, notifications=notifications, preferences=preferences)
    else:
        return redirect(url_for('login'))
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        location = request.form.get('location', '')
        job_type = request.form.get('job_type', '')
        
        query_conditions = []
        query_values = []

        if location:
            query_conditions.append("location LIKE %s")
            query_values.append(f'%{location}%')
        if job_type:
            query_conditions.append("type LIKE %s")
            query_values.append(f'%{job_type}%')

        if query_conditions:
            sql_query = f"SELECT * FROM jobs WHERE {' AND '.join(query_conditions)}"
        else:
            sql_query = "SELECT * FROM jobs"

        cursor.execute(sql_query, query_values)
        filtered_jobs = cursor.fetchall()
        return render_template('job_list.html', jobs=filtered_jobs)
    
    return render_template('job_list.html', jobs=[])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx'}

@app.route('/apply_job/<int:job_id>', methods=['GET'])
def apply_job(job_id):
    if 'loggedin' in session:
        cursor.execute('SELECT title FROM jobs WHERE job_id = %s', (job_id,))
        job = cursor.fetchone()
        if job:
            return render_template('apply_job.html', job_id=job_id, job_title=job[0])
        else:
            return 'Job not found', 404
    else:
        return redirect(url_for('login'))
@app.route('/submit_application/<int:job_id>', methods=['POST'])
def submit_application(job_id):
    if 'loggedin' in session and session['role'] == 'job_seeker':
        cover_letter = request.form['cover_letter']
        resume = request.files['resume']
        user_id = session['id']

        if resume and allowed_file(resume.filename):
            filename = secure_filename(resume.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(resume_path)

            cursor.execute(
                'INSERT INTO applications (job_id, job_seeker_id, cover_letter, resume, status) VALUES (%s, %s, %s, %s, %s)',
                (job_id, user_id, cover_letter, filename, 'accepted')
            )
            conn.commit()
            return 'Application submitted successfully!'
        else:
            return 'Invalid file type', 400
    else:
        return redirect(url_for('login'))

@app.route('/application_status')
def application_status():
    if 'loggedin' in session and session['role'] == 'job_seeker':
        user_id = session['id']
        cursor.execute('SELECT a.app_id, j.title, a.cover_letter, a.resume, a.status FROM applications a JOIN jobs j ON a.job_id = j.job_id WHERE a.job_seeker_id = %s', (user_id,))
        applications = cursor.fetchall()
        return render_template('application_status.html', applications=applications)
    else:
        return redirect(url_for('login'))
@app.route('/delete_application', methods=['POST'])
def delete_application():
    if 'loggedin' in session and session['role'] == 'job_seeker':
        application_id = request.form['application_id']

        cursor.execute('SELECT resume FROM applications WHERE app_id = %s', (application_id,))
        resume_path = cursor.fetchone()

        if resume_path:
            try:
                os.remove(resume_path[0])
            except OSError as e:
                print(f"Error: {resume_path[0]} : {e.strerror}")

        cursor.execute('DELETE FROM applications WHERE app_id = %s', (application_id,))
        conn.commit()

        return redirect(url_for('application_status'))
    else:
        return redirect(url_for('login'))

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/view_applications/<int:job_id>')
def view_applications(job_id):
    if 'loggedin' in session and session['role'] == 'employer':
        cursor.execute('SELECT a.app_id, js.name, a.cover_letter, a.resume, a.status FROM applications a JOIN job_seekers js ON a.job_seeker_id = js.id WHERE a.job_id = %s', (job_id,))
        applications = cursor.fetchall()
        cursor.execute('SELECT title FROM jobs WHERE job_id = %s', (job_id,))
        job_title = cursor.fetchone()[0]
        return render_template('view_applications.html', applications=applications, job_title=job_title)
    else:
        return redirect(url_for('application_status'))
@app.route('/update_application_status', methods=['POST'])
def update_application_status():
    if 'loggedin' in session and session['role'] == 'employer':
        application_id = request.form['application_id']
        new_status = request.form['status']
        cursor.execute('UPDATE applications SET status = %s WHERE app_id = %s', (new_status, application_id))
        conn.commit()
        return redirect(url_for('employer_dashboard'))
    else:
        return redirect(url_for('login'))
@app.route('/send_message', methods=['POST', 'GET'])
def send_message():
    if 'loggedin' in session:
        if request.method == 'POST':
            sender_id = session['id']
            receiver_id = request.form.get('receiver_id')
            content = request.form.get('content')
            
            logging.debug(f"Sender ID: {sender_id}, Receiver ID: {receiver_id}, Content: {content}")
            
            if not receiver_id or not content:
                flash('Receiver ID and content are required.')
                return redirect(url_for('view_messages', user_id=receiver_id if receiver_id else sender_id))
            
            try:
                receiver_id = int(receiver_id)
            except ValueError:
                flash('Invalid Receiver ID.')
                return redirect(url_for('view_messages', user_id=sender_id))
            
            cursor.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (%s, %s, %s)',
                           (sender_id, receiver_id, content))
            conn.commit()
            
            return redirect(url_for('view_messages', user_id=receiver_id))
        else:
            return redirect(url_for('view_messages', user_id=session['id']))
    else:
        return redirect(url_for('login'))

@app.route('/view_messages/<int:user_id>')
def view_messages(user_id):
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM messages WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s) ORDER BY timestamp',
                       (session['id'], user_id, user_id, session['id']))
        messages = cursor.fetchall()
        
        cursor.execute('SELECT name FROM users WHERE user_id = %s', (user_id,))
        recipient_name = cursor.fetchone()[0] 
        
        return render_template('view_messages.html', messages=messages, recipient_name=recipient_name, user_id=user_id)
    else:
        return redirect(url_for('login'))
@app.route('/set_preferences', methods=['GET', 'POST'])
def set_preferences():
    if 'loggedin' in session and session['role'] == 'job_seeker':
        if request.method == 'POST':
            keyword = request.form['keyword']
            location = request.form['location']
            category = request.form['category']
            
            cursor.execute("SELECT * FROM job_preferences WHERE job_seeker_id = %s", (session['id'],))
            preference = cursor.fetchone()
            if preference:
                cursor.execute("UPDATE job_preferences SET keyword = %s, location = %s, category = %s WHERE job_seeker_id = %s", (keyword, location, category, session['id']))
            else:
                cursor.execute("INSERT INTO job_preferences (job_seeker_id, keyword, location, category) VALUES (%s, %s, %s, %s)", (session['id'], keyword, location, category))
            conn.commit()
            return redirect(url_for('jobseeker_dashboard'))
        else:
            return render_template('set_preferences.html')
    else:
        return redirect(url_for('login'))
@app.route('/notifications')
def notifications():
    if 'loggedin' in session and session['role'] == 'job_seeker':
        cursor.execute("SELECT * FROM notifications WHERE job_seeker_id = %s AND is_read = FALSE", (session['id'],))
        notifications = cursor.fetchall()
        return render_template('notifications.html', notifications=notifications)
    else:
        return redirect(url_for('login'))
@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'loggedin' in session and session['role'] == 'employer':
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            requirements = request.form['requirements']
            location = request.form['location']
            category = request.form['category']
            
            cursor.execute("INSERT INTO jobs (title, description, requirements, location, category) VALUES (%s, %s, %s, %s, %s)", (title, description, requirements, location, category))
            conn.commit()
            
            job_id = cursor.lastrowid
            
            # Fetch job seekers matching the preferences
            cursor.execute("SELECT job_seeker_id FROM job_preferences WHERE (keyword = %s OR location = %s OR category = %s)", (title, location, category))
            matching_users = cursor.fetchall()
            for user in matching_users:
                cursor.execute("INSERT INTO notifications (job_seeker_id, job_id, message) VALUES (%s, %s, %s)", (user['job_seeker_id'], job_id, f"New job posted: {title} in {category}, {location}"))
            conn.commit()
            
            return redirect(url_for('employer_dashboard'))
        else:
            return render_template('post_job.html')
    else:
        return redirect(url_for('login'))
@app.route('/mark_as_read/<int:notification_id>')
def mark_as_read(notification_id):
    if 'loggedin' in session and session['role'] == 'job_seeker':
        cursor.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s AND job_seeker_id = %s", (notification_id, session['id']))
        conn.commit()
        return redirect(url_for('jobseeker_dashboard'))
    else:
        return redirect(url_for('login'))

    

if __name__ == '__main__':
    app.run(debug=True)
