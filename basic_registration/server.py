from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
import re
from mysqlconnection import connectToMySQL

app = Flask(__name__)
app.secret_key = "Welcome to the thunder dome"
bcrpyt = Bcrypt(app)

@app.route("/")
def home():
    mysql = connectToMySQL("registration")
    users = mysql.query_db("SELECT * FROM users;")
    print(users)
    return render_template("index.html", all_users = users)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

@app.route("/username", methods=['POST'])
def username():
    found = False
    mysql = connectToMySQL("registration")
    query = "SELECT username from users WHERE users.username = %(user)s;"
    data = {
        'user': request.form['username']
    }
    result = mysql.query_db(query,data)
    if result:
        found = True
    return render_template('/partials/username.html', found = found)

@app.route("/create_user", methods=['POST'])
def create_user():
    is_valid = True
    SpecialSym = ['$','@', '#', '%']
    
    if len(request.form['username']) < 1:
        is_valid = False
        flash("Please enter a valid username")
    
    if not EMAIL_REGEX.match(request.form['email']):
        is_valid = False
        flash("Invalid email address!")
    
    if len(request.form['pass']) < 5:
        is_valid = False
        flash("Password Must Be At Least 5 Characters")
    
    if request.form['cpass'] != request.form ['pass']:
        is_valid = False
        flash("Incorrect Password")
    
    if not request.form['username'].isalpha():
        is_valid = False
        flash("Username can only contain alphabetic characters")
    
    if not any(char.isdigit() for char in request.form['pass']): 
        is_valid = False
        flash('Password should have at least one numeral') 
    
    if not any(char.isupper() for char in request.form['pass']): 
        is_valid = False
        flash('Password should have at least one uppercase letter') 
    
    if not any(char.islower() for char in request.form['pass']): 
        is_valid = False
        flash('Password should have at least one lowercase letter') 
    
    if not any(char in SpecialSym for char in request.form['pass']): 
        is_valid = False
        flash('Password should have at least one of the symbols $@#')
    
    mysql = connectToMySQL("registration")
    validate_email_query = 'SELECT id FROM users WHERE email=%(email)s;'
    form_data = {
        'email': request.form['email']
    }
    existing_users = mysql.query_db(validate_email_query, form_data)

    if existing_users:
        flash("Email already in use")
        is_valid = False
    
    if is_valid:
        mysql = connectToMySQL("registration")
        pw_hash = bcrpyt.generate_password_hash(request.form['pass'])
        query = "INSERT into users(username, email, password, created_at, updated_at) VALUES (%(username)s, %(email)s, %(password_hash)s, NOW(), NOW());"

        data = {
            "username": request.form['username'],
            "email": request.form['email'],
            "password_hash": pw_hash
        }
        result_id = mysql.query_db(query, data)
        session['username'] = request.form['username']
        flash("Successfully added:{}".format(result_id))
        return redirect("/success")
    return redirect("/")

@app.route('/user_search', methods=["POST"])
def search():
    mysql = connectToMySQL("registration")
    query = "SELECT username FROM users WHERE username LIKE %%(search_term)s;"
    data = {
        "search_term": f"{request.form.get('search_term')}%"
    }
    result = mysql.query_db(query,data)
    return render_template("/partials/search_results.html", result = result)

@app.route('/login', methods=['POST'])
def login():
    mysql = connectToMySQL("registration")
    query = "SELECT * FROM users WHERE email = %(email)s;"
    data = { "email": request.form['email'] }
    result = mysql.query_db(query,data)
    if result: 
        if bcrpyt.check_password_hash(result[0]['password'], request.form['pass']):
            session['username'] = result[0]['username']
            return redirect("/success")
    flash("You could not be logged in")
    return redirect("/")

@app.route('/success')
def success():
    if 'username' not in session: 
        return redirect("/")
    return render_template("welcome.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("You have successfully logged yourself out")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)