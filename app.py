import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import csv
import bcrypt
from werkzeug.utils import secure_filename
from datetime import timedelta

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Secret key for session management

# Set up file upload configurations
UPLOAD_FOLDER = 'uploads'  # Directory where uploaded files will be stored
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CSV_FILE = 'users.csv'  # CSV file to store user data
INSTRUMENT_FILE = 'instruments.csv'  # CSV file to store instrument data
SIGNUP_KEY = '123'  # Required sign-up key for user registration

app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Move uploads folder to static


# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
def register_user(first_name, last_name, email, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with open(CSV_FILE, mode='a', newline='') as file:
        fieldnames = ['first_name', 'last_name', 'email', 'password']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()  # Write header if file is empty
        writer.writerow({'first_name': first_name, 'last_name': last_name, 'email': email, 'password': hashed_password.decode('utf-8')})

# Helper function to authenticate a user
def authenticate_user(email, password):
    try:
        with open(CSV_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['email'] == email:
                    if bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
                        return f"{row['first_name']} {row['last_name']}"
        return None
    except FileNotFoundError:
        return None

# Helper function to get unique values from the instrument CSV for dropdowns
def get_dropdown_values():
    brands = set()
    types = set()
    conditions = set()
    try:
        with open(INSTRUMENT_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                brands.add(row['brand'])
                types.add(row['instrument_type'])
                conditions.add(row['condition'])
    except FileNotFoundError:
        pass  # If file doesn't exist yet, it's fine; dropdowns will be empty
    return list(brands), list(types), list(conditions)

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
        first_name = request.form['first_name']
        last_name = request.form['last_name']
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
            register_user(first_name, last_name, email, password)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

# Route for the home page (after login)
@app.route('/home')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])
    return redirect(url_for('login'))

# Route to add a new instrument (only accessible if logged in)
@app.route('/add_instrument', methods=['GET', 'POST'])
def add_instrument():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        brand = request.form['brand'] if request.form['brand'] != 'Add new...' else request.form['new_brand']
        instrument_type = request.form['instrument_type'] if request.form['instrument_type'] != 'Add new...' else request.form['new_instrument_type']
        serial_number = request.form['serial_number']
        uuid_code = request.form['uuid']  # Manually entered or scanned UUID
        condition = request.form['condition'] if request.form['condition'] != 'Add new...' else request.form['new_condition']
        checked_out = 'checked_out' in request.form  # True if checked out
        location = request.form['location'] if not checked_out else ''
        student_name = request.form['student_name'] if checked_out else ''
        grad_year = request.form['grad_year'] if checked_out else ''
        student_id = request.form['student_id'] if checked_out else ''
        notes = request.form['notes']

        # Handle file uploads (Images)
        uploaded_files = request.files.getlist('images')
        image_filenames = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_filenames.append(filename)

        # Ensure at least one image is uploaded
        if not image_filenames:
            flash('You must upload at least one image!', 'error')
            return redirect(url_for('add_instrument'))

        # Write the instrument data to the CSV file
        with open(INSTRUMENT_FILE, mode='a', newline='') as file:
            fieldnames = ['brand', 'instrument_type', 'serial_number', 'uuid', 'condition', 'checked_out', 'location', 'student_name', 'grad_year', 'student_id', 'notes', 'images']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()  # Write header if file is empty
            writer.writerow({
                'brand': brand,
                'instrument_type': instrument_type,
                'serial_number': serial_number,
                'uuid': uuid_code,
                'condition': condition,
                'checked_out': 'Yes' if checked_out else 'No',
                'location': location,
                'student_name': student_name,
                'grad_year': grad_year,
                'student_id': student_id,
                'notes': notes,
                'images': ';'.join(image_filenames)  # Store image filenames as a semicolon-separated string
            })

        flash('Instrument added successfully!', 'success')
        return redirect(url_for('add_instrument'))

    # Load dropdown values
    brands, types, conditions = get_dropdown_values()
    return render_template('add_instrument.html', brands=brands, types=types, conditions=conditions)

# Helper function to read the instruments list from the CSV file
def get_instruments():
    instruments = []
    try:
        with open(INSTRUMENT_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                instruments.append(row)
    except FileNotFoundError:
        pass  # If file doesn't exist, return an empty list
    return instruments

# Route to display the list of instruments
@app.route('/instruments')
def instruments():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    instruments_list = get_instruments()  # Get all instruments

    # Get filters from the request args
    selected_brand = request.args.get('brand')
    selected_type = request.args.get('instrument_type')
    selected_condition = request.args.get('condition')
    selected_checked_out = request.args.get('checked_out')
    sort_by = request.args.get('sort_by', 'brand')  # Default sort by brand

    # Apply filters
    if selected_brand:
        instruments_list = [i for i in instruments_list if i['brand'] == selected_brand]
    if selected_type:
        instruments_list = [i for i in instruments_list if i['instrument_type'] == selected_type]
    if selected_condition:
        instruments_list = [i for i in instruments_list if i['condition'] == selected_condition]
    if selected_checked_out:
        instruments_list = [i for i in instruments_list if i['checked_out'] == selected_checked_out]

    # Apply sorting
    instruments_list.sort(key=lambda x: x[sort_by])

    # Get dropdown values for filters
    brands, types, conditions = get_dropdown_values()

    return render_template('instruments.html', 
                           instruments=instruments_list, 
                           brands=brands, 
                           types=types, 
                           conditions=conditions)

@app.route('/edit_instrument/<uuid>', methods=['GET', 'POST'])
def edit_instrument(uuid):
    if 'user' not in session:
        return redirect(url_for('login'))

    instruments_list = get_instruments()  # Get all instruments
    instrument_to_edit = next((i for i in instruments_list if i['uuid'] == uuid), None)

    if not instrument_to_edit:
        flash('Instrument not found!', 'error')
        return redirect(url_for('instruments'))

    if request.method == 'POST':
        # Update the instrument details with the form data
        instrument_to_edit['brand'] = request.form['brand']
        instrument_to_edit['instrument_type'] = request.form['instrument_type']
        instrument_to_edit['serial_number'] = request.form['serial_number']
        instrument_to_edit['condition'] = request.form['condition']
        instrument_to_edit['checked_out'] = 'Yes' if 'checked_out' in request.form else 'No'
        instrument_to_edit['location'] = request.form['location']
        instrument_to_edit['student_name'] = request.form['student_name']
        instrument_to_edit['grad_year'] = request.form['grad_year']
        instrument_to_edit['student_id'] = request.form['student_id']
        instrument_to_edit['notes'] = request.form['notes']

        # Update the CSV file with the new information
        with open(INSTRUMENT_FILE, mode='w', newline='') as file:
            fieldnames = ['brand', 'instrument_type', 'serial_number', 'uuid', 'condition', 'checked_out', 'location', 'student_name', 'grad_year', 'student_id', 'notes', 'images']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(instruments_list)  # Write updated instrument list

        flash('Instrument updated successfully!', 'success')
        return redirect(url_for('instruments'))

    # Pre-fill the form with the current instrument data
    return render_template('edit_instrument.html', instrument=instrument_to_edit)



@app.route('/delete_instrument/<uuid>', methods=['POST'])
def delete_instrument(uuid):
    if 'user' not in session:
        return redirect(url_for('login'))

    instruments_list = get_instruments()  # Get all instruments
    updated_instruments = [i for i in instruments_list if i['uuid'] != uuid]

    # Write the updated instrument list back to the CSV file
    with open(INSTRUMENT_FILE, mode='w', newline='') as file:
        fieldnames = ['brand', 'instrument_type', 'serial_number', 'uuid', 'condition', 'checked_out', 'location', 'student_name', 'grad_year', 'student_id', 'notes', 'images']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_instruments)

    flash('Instrument deleted successfully!', 'success')
    return redirect(url_for('instruments'))

# Route for logging out
@app.route('/logout')
def logout():
    session.pop('user', None)
    response = make_response(redirect(url_for('login')))
    response.set_cookie('user', '', expires=0)  # Clear the cookie by setting its expiration date in the past
    flash('You have been logged out.', 'info')
    return response

# Custom error handler for 404 errors (Page Not Found)
@app.errorhandler(404)
def page_not_found(e):
    if 'user' in session or request.cookies.get('user'):
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
