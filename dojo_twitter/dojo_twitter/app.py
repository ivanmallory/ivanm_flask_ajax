from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = "Welcome to the thunder dome"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dojo_tweets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

db = SQLAlchemy(app)
migrate = Migrate (app, db)

bcrpyt = Bcrypt(app)

likes_table = db.Table('likes', 
                db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key = True), 
                db.Column('tweet_id', db.Integer, db.ForeignKey('tweet.id'), primary_key = True))

follow_table = db.Table('following', 
                db.Column('followed', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                db.Column('follower', db.Integer, db.ForeignKey('user.id'), primary_key=True))

class User(db.Model):
    id = db.Column (db.Integer, primary_key=True)
    first_name = db.Column(db.String(45))
    last_name = db.Column(db.String(45))
    email = db.Column(db.String(45))
    password = db.Column(db.String(70))
    tweets_this_user_likes = db.relationship('Tweet', secondary=likes_table, backref="users_who_like_this_tweet")

    users_this_user_is_following = db.relationship('User', secondary=follow_table,
                                primaryjoin="User.id==following.c.follower",
                                secondaryjoin="User.id==following.c.followed")
    users_who_follow_this_user = db.relationship('User', secondary=follow_table, 
                                primaryjoin="User.id==following.c.followed", 
                                secondaryjoin="User.id==following.c.follower")

    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

class Tweet(db.Model):
    id = db.Column (db.Integer, primary_key=True)
    content = db.Column(db.String(255))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', foreign_keys=[author_id], backref="user_tweets")
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_user', methods=['POST'])
def create_user():
    is_valid = True
    SpecialSym = ['$','@', '#', '%']
    
    if len(request.form['fname']) < 1:
        is_valid = False
        flash("Please enter a first name")
    
    if len(request.form['lname']) < 1:
        is_valid = False
        flash("Please enter a last name")
    
    if not EMAIL_REGEX.match(request.form['email']):
        is_valid = False
        flash("Invalid email address!")
    
    if len(request.form['pass']) < 5:
        is_valid = False
        flash("Password Must Be At Least 5 Characters")
    
    if request.form['cpass'] != request.form ['pass']:
        is_valid = False
        flash("Incorrect Password")
    
    if not request.form['fname'].isalpha():
        is_valid = False
        flash("First name can only contain alphabetic characters")
    
    if not request.form['lname'].isalpha():
        is_valid = False
        flash("Last name can only contain alphabetic characters")
    
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

    if is_valid:
        pw_hash = bcrpyt.generate_password_hash(request.form['pass'])
        user = User(first_name=request.form['fname'], last_name = request.form['lname'], email = request.form['email'], password = pw_hash)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id

        flash("Successfully added:{}".format(user.id))
        return redirect("/success")
    else:
        return redirect("/")

@app.route('/login', methods=['POST'])
def login():
    is_valid = True
    if not request.form['email']:
        is_valid = False
        flash("Please enter an email")

    if not EMAIL_REGEX.match(request.form['email']):
        is_valid = False
        flash("Please enter a valid email")

    if not is_valid:
        return redirect("/")

    else:

        user_list = User.query.filter_by(email = request.form['email']).all()
        if not user_list:
            flash("Email is not valid")
            return redirect("/")
        else:
            user = user_list[0]
        
        if not request.form['pass']:
            is_valid = False
            flash("Please enter a password")

        if not bcrpyt.check_password_hash(user.password, request.form['pass']):
            is_valid = False
            flash("Password is not valid")

        if is_valid:
            session['user_id'] = user.id
            return redirect("/success")
        else:
            flash("You could not be logged in")
            return redirect("/")

@app.route('/success')
def success():
    if 'user_id' not in session: 
        return redirect("/")

    user = User.query.get(session['user_id'])

    tweets = []
    u_f = user.users_this_user_is_following
    for u in u_f:
        tweets.extend(u.user_tweets)
    tweets.extend(user.user_tweets)

    liked_tweet_ids = user.tweets_this_user_likes

    for tweet in tweets:
        td = datetime.now() - tweet.created_at
        if td.seconds == 0:
            tweet.time_since_secs = 1
        if td.seconds < 60 and td.seconds > 0:
            tweet.time_since_secs = td.seconds
        if td.seconds < 3600:
            tweet.time_since_minutes = round(td.seconds/60) % 60
        if td.seconds > 3660:
            tweet.time_since_hours = round(td.seconds/3600)
        if td.days > 0:
            tweet.time_since_days = td.days
        
        for tweet in tweets:
            tweet.like_count = len(tweet.users_who_like_this_tweet)
        
    if user:
        return render_template("dashboard.html", user_data = user, tweet_data = tweets, liked_tweet_ids = liked_tweet_ids)
    else:
        return render_template("dashboard.html") 

@app.route('/success_v2')
def success_v2():
    if 'user_id' not in session: 
        return redirect("/")

    user = User.query.get(session['user_id'])

    tweets = []
    u_f = user.users_this_user_is_following
    for u in u_f:
        tweets.extend(u.user_tweets)
    tweets.extend(user.user_tweets)

    liked_tweet_ids = user.tweets_this_user_likes

    for tweet in tweets:
        td = datetime.now() - tweet.created_at
        if td.seconds == 0:
            tweet.time_since_secs = 1
        if td.seconds < 60 and td.seconds > 0:
            tweet.time_since_secs = td.seconds
        if td.seconds < 3600:
            tweet.time_since_minutes = round(td.seconds/60)
        if td.seconds > 3660:
            tweet.time_since_hours = round(td.seconds/3600)
        if td.days > 0:
            tweet.time_since_days = td.days
        
        for tweet in tweets:
            tweet.like_count = len(tweet.users_who_like_this_tweet)
        
    if user:
        return render_template("fragments/tweet_body.html", user_data = user, tweet_data = tweets, liked_tweet_ids = liked_tweet_ids)
    else:
        return redirect("/")

@app.route('/tweets/create', methods=["POST"])
def create_tweet():
    is_valid = True
    if len(request.form['tweet']) < 1:
        is_valid = False
        flash("Tweet must be between 1-255 characters")
    if len(request.form['tweet']) > 255:
        is_valid = False
        flash("Tweet must be between 1-255 characters")

    if is_valid:
        tweet = Tweet(content = request.form['tweet'],
        author_id = session['user_id'])
        db.session.add(tweet)
        db.session.commit()
        return render_template("fragments/tweet_content.html", tweet=tweet)
    else:
        return "False"

@app.route('/like_tweet/<tweet_id>')
def like_tweet(tweet_id):
    tweet = Tweet.query.get(tweet_id)
    user = User.query.get(session['user_id'])
    user.tweets_this_user_likes.append(tweet)
    db.session.commit()

    return redirect("/success")

@app.route('/unlike_tweet/<tweet_id>')
def unlike_tweet(tweet_id):
    user = User.query.get(session['user_id'])
    tweet = Tweet.query.get(tweet_id)
    user.tweets_this_user_likes.remove(tweet)
    db.session.commit()

    return redirect("/success")

@app.route('/edit_tweet/<tweet_id>')
def edit_tweet(tweet_id):
    tweet = Tweet.query.get(tweet_id)
    if not tweet:
        return redirect("/success")
    else:
        return render_template("edit.html", tweet_data = tweet)

@app.route('/update_tweet/<tweet_id>', methods=["POST"])
def update_tweet(tweet_id):
    tweet = Tweet.query.get(tweet_id)
    tweet.content = request.form['tweet']
    db.session.commit()
    return redirect(f"/tweet_details/{tweet_id}")

@app.route('/delete_tweet/<tweet_id>')
def delete_tweet(tweet_id):
    tweet = Tweet.query.get(tweet_id)
    db.session.delete(tweet)
    db.session.commit()

    return redirect('/success')

@app.route('/tweet_details/<tweet_id>') 
def tweet_details(tweet_id):
    tweet = Tweet.query.get(tweet_id)
    if not tweet:
        return redirect("/success")
    else:
        user_who_have_liked = tweet.users_who_like_this_tweet
    return render_template("tweet_details.html", tweet = tweet, user_who_have_liked = user_who_have_liked)

@app.route('/users')
def users_to_follow():
    user = User.query.get(session['user_id'])
    all_users = User.query.filter(User.id != user.id).all()
    users_to_follow = [u for u in all_users if u not in user.users_this_user_is_following]
    return render_template("users.html", users_to_follow = users_to_follow, all_users = all_users)

@app.route('/follow/<user_id>')
def follow_user(user_id):
    user_to_follow = User.query.get(user_id)
    signed_in_user = User.query.get(session['user_id'])
    signed_in_user.users_this_user_is_following.append(user_to_follow)
    db.session.commit()
    return redirect("/users")

@app.route('/unfollow/<user_id>')
def unfollow_user(user_id):
    user_to_unfollow = User.query.get(user_id)
    user = User.query.get(session['user_id'])
    user.users_this_user_is_following.remove(user_to_unfollow)
    db.session.commit()
    return redirect("/users")

@app.route('/logout')
def logout():
    session.clear()
    flash("You have successfully logged yourself out")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)