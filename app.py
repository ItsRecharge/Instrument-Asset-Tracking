from flask import Flask, render_template, request, redirect, url_for, session, flash

# Create a Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed to use sessions

# Hard-coded credentials (for simplicity)
USERNAME = 'admin'
PASSWORD = 'password123'

# Route for the sign-in (login) page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the username and password from the form
        username = request.form['username']
        password = request.form['password']
        
        # Simple authentication check
        if username == USERNAME and password == PASSWORD:
            session['user'] = username  # Store username in session
            return redirect(url_for('home'))  # Redirect to home page
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')  # Render the login form

# Route for the home page (after login)
@app.route('/home')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])  # Show home page with user name
    else:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))

# Route for logging out
@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove the user from the session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
