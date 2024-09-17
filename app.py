from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import csv
import bcrypt
from datetime import timedelta

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Secret key for session management
CSV_FILE = 'users.csv'  # CSV file to store user data
SIGNUP_KEY = '123'  # Required sign-up key for user registration

# Helper function to check if a user exists by email
def user_exists(email):
    try:
        with open(CSV_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['email'] == email:
                    return True
        return False
    except FileNotFoundError:
        return False

# Helper function to register a new user
def register_user(name, email, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with open(CSV_FILE, mode='a', newline='') as file:
        fieldnames = ['name', 'email', 'password']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()  # Write header if file is empty
        writer.writerow({'name': name, 'email': email, 'password': hashed_password.decode('utf-8')})

# Helper function to authenticate a user
def authenticate_user(email, password):
    try:
        with open(CSV_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['email'] == email:
                    # Check if the password matches the hashed password
                    if bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
                        return row['name']
        return None
    except FileNotFoundError:
        return None

# Global check for authentication and redirect logic before every request
@app.before_request
def check_user_authentication():
    # Allow access to these routes without redirection
    allowed_routes = ['login', 'signup', 'static']

    # Check if user is already logged in via session or cookie
    if 'user' not in session:
        user = request.cookies.get('user')
        if user:
            session['user'] = user  # Automatically log the user in using the cookie
        elif request.endpoint not in allowed_routes:
            # Redirect to login if not authenticated and trying to access a restricted route
            return redirect(url_for('login'))

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = 'remember_me' in request.form  # Check if 'Remember Me' checkbox is checked

        # Authenticate the user
        user = authenticate_user(email, password)
        if user:
            session['user'] = user
            response = make_response(redirect(url_for('home')))

            if remember_me:
                # Set a cookie to remember the user for 30 days
                response.set_cookie('user', user, max_age=30*24*60*60)  # Cookie valid for 30 days

            return response
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template('login.html')

# Route for the sign-up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('home'))  # Redirect to home if already logged in

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        signup_key = request.form['signup_key']

        # Validate sign-up key
        if signup_key != SIGNUP_KEY:
            flash('Invalid sign-up key!', 'error')
            return render_template('signup.html')

        # Check if user already exists
        if user_exists(email):
            flash('User already exists with this email!', 'error')
        else:
            # Register the user
            register_user(name, email, password)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

# Route for the home page (after login)
@app.route('/home')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])
    
    # This line will likely never be reached because of the global check,
    # but we'll keep it as a fallback in case someone tries to manually access /home.
    return redirect(url_for('login'))

# Route for logging out
@app.route('/logout')
def logout():
    session.pop('user', None)
    response = make_response(redirect(url_for('login')))
    response.set_cookie('user', '', expires=0)  # Clear the cookie by setting its expiration date in the past
    flash('You have been logged out.', 'info')
    return response

if __name__ == '__main__':
    app.run(debug=True)
