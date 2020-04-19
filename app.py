######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Yuxuan Ji <yuxuanji@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
#import flask.ext.login as flask_login
import flask_login
#for image uploading
from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'pass1234'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader#memorizing each user
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password,first_name FROM users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@app.route('/top', methods=['GET'])
def viewtop():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, first_name, last_name,score FROM users WHERE user_id>0 ORDER BY score DESC LIMIT 5")
	top = cursor.fetchall()
	return render_template('top.html', tops = top)

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register/", methods=['GET'])
def register():
	return render_template('improved_register.html', supress='True')  

@app.route("/register/", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
                print (email)
		password=request.form.get('password')
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		dob=request.form.get('dob')
		gender=request.form.get('gender')
		home=request.form.get('hometown')
		bio=request.form.get('bio')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print (cursor.execute("INSERT INTO users (email, password, first_name, last_name, dob, gender, hometown, bio) "
							  "VALUES ('{0}', '{1}', '{2}','{3}','{4}','{5}','{6}','{7}')".format(email, password,first_name,
																								  last_name, dob,gender,home,bio)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print ("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))
#end login code

#DEFINE FUNCTIONS
#all photos for the current user
def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT p.data, p.pid, p.caption, a.name, a.aid FROM photo p, albums a,users u "
				   "WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND p.aid = a.aid".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

#all photoID for photos owned by current user
def getUsersPhotoIDs(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT pid FROM photo WHERE u.user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

#all photoID for photos that have tags associate(owned by the current user)
def getUserPhotoHaveTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT t.pid FROM tag_associate t, photo p, albums a, users u "
				   " WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid AND p.pid = t.pid".format(uid))
	return cursor.fetchall()

#all tags for photos owned by the current user
def getUserPhotoTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT t.description, t.pid FROM tag_associate t, photo p, albums a, users u "
				   " WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid AND p.pid = t.pid".format(uid))
	return cursor.fetchall()

#all photoID for photo with comment owned by the current user
def getUserPhotoHaveComments(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT c.pid FROM comment_on c, photo p, albums a, users u "
				   " WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid AND p.pid = c.pid".format(uid))
	return cursor.fetchall()

#all comments for photos owned by the current user
def getUserPhotoComments(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT c.text, c.pid FROM comment_on c, photo p, albums a, users u "
				   " WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid AND p.pid = c.pid".format(uid))
	return cursor.fetchall()
##end of getting user photo related

#all photoID for photo with likes owned by the current user
def getUserPhotoHaveLikes(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT l.pid FROM likes l, photo p, albums a, users u "
				   " WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid AND p.pid = l.pid".format(uid))
	return cursor.fetchall()

#all likes for photos owned by the current user
def getUserPhotoLikes(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT l.pid, u.first_name, u.last_name FROM likes l, users u, "
				   "(SELECT p.pid FROM photo p, albums a, users u WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND a.aid = p.aid)X "
				   "WHERE l.user_id = u.user_id AND X.pid = l.pid".format(uid))
	return cursor.fetchall()

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

#all albums that belong to the current user
def getUsersAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT name,aid FROM albums WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True

def isOwnPhoto(uid, pid):
	#use this to check if user is trying to add tags to their own photo.
	cursor = conn.cursor()
	if cursor.execute("SELECT p.pid FROM photo p, albums a, users u WHERE u.user_id = '{0}' AND a.user_id = u.user_id "
					  "AND a.aid = p.aid AND p.pid = '{1}'".format(uid, pid)):
		return True
	else:
		return False

def isTagCreateNeed(tag):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM tags WHERE description='{0}'".format(tag)):
	# check if the input tag need to be create, if already exit, then do not need to be created.
		return False
	else:
		return True

#check if the input userID valid
def isFriendExist(fid):
	cursor = conn.cursor()
	if cursor.execute("SELECT user_id FROM users WHERE user_id='{0}'".format(fid)):
		return True
	else:
		return False

#check if has already added user with "fri" as friend
def isFriendAlready(uid, fid):
	cursor = conn.cursor()
	if cursor.execute("SELECT user_id, fri_id FROM friends WHERE user_id='{0}' AND fri_id = '{1}'".format(uid, fid)):
		return True
	else:
		return False

def AllUsers():
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT user_id, first_name, last_name FROM users WHERE user_id > 0 ")
	return cursor.fetchall()

def AllUserAlbums():
	cursor = conn.cursor()
	cursor.execute("SELECT aid, name, user_id FROM albums")
	return cursor.fetchall()

#user_id of user who have at least one album
def AllUserHaveAlbum():
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT aid, user_id FROM albums")
	return cursor.fetchall()

#user_id of user who doesn't have album
def AllUserNoAlbum():
	cursor = conn.cursor()
	cursor.execute("SELECT u.user_id FROM users u WHERE u.user_id not in (SELECT DISTINCT a.user_id FROM albums a)")
	return cursor.fetchall()

#check whether a user is trying to add himself as a friend
def isSame(uid,fid):
	cursor = conn.cursor()
	if isFriendExist(fid):
		if isFriendAlready(uid, fid):
			return False
		else:
			cursor.execute("INSERT INTO friends VALUES ('{0}','{1}')".format(uid, fid))
			if cursor.execute("SELECT user_id, fri_id FROM friends WHERE user_id='{0}' AND fri_id = '{1}'".format(uid, uid)):
				return True
			else:
				cursor.execute("DELETE FROM friends WHERE user_id='{0}' AND fri_id = '{1}'".format(uid, fid))
				return False
	else:
		return False

@app.route('/friend', methods=['POST','GET'])
@flask_login.login_required
def add_friend():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		fid = request.form.get('fid')
		if isSame(uid,fid):
			return render_template('friends.html', message='Invalid User ID! You cannot friend yourself!',
							 	    users=AllUsers(), albums=AllUserAlbums(), friend=True, havealbum=AllUserHaveAlbum()
								   ,noalbum=AllUserNoAlbum())
		else:
			if isFriendExist(fid):
				if isFriendAlready(uid, fid):
					return render_template('friends.html', message='Already Friends! No need to add!',
										   users=AllUsers(), albums=AllUserAlbums(), havealbum=AllUserHaveAlbum(),
										   noalbum=AllUserNoAlbum())
				else:
					cursor = conn.cursor()
					cursor.execute("INSERT INTO friends (user_id, fri_id) VALUES ('{0}','{1}')".format(uid, fid))
					conn.commit()
					return render_template('friends.html', message='Friend Added! You can view it on your profile page.!',
										   users=AllUsers(), albums=AllUserAlbums(), havealbum=AllUserHaveAlbum(),
										   noalbum=AllUserNoAlbum())
			else:
				return render_template('friends.html', message='Invalid User ID! Please enter existed userID!',
								   	users=AllUsers(), albums=AllUserAlbums(), friend=True, havealbum=AllUserHaveAlbum()
									   , noalbum=AllUserNoAlbum())
	else:
		return render_template('friends.html', users=AllUsers(), albums=AllUserAlbums(), havealbum=AllUserHaveAlbum(),
							   friend=True, noalbum=AllUserNoAlbum())

@app.route('/searchfriend',methods=['GET','POST'])
@flask_login.login_required
def search_friend():
	if request.method == 'POST':
		uid=getUserIdFromEmail(flask_login.current_user.id)
		name=request.form.get('name')
		name=name.split(" ")
		n=len(name)
		if n != 2:
			return render_template('friends.html', byname=True, message='Invalid Input! Please enter again!')
		else:
			cursor=conn.cursor()
			if cursor.execute("SELECT u.user_id, u.first_name, u.last_name FROM users u WHERE u.first_name='{0}' AND u.last_name='{1}'".format(name[0],name[1])):
				user=cursor.fetchall()
				cursor.execute("SELECT a.aid,a.name,u.user_id FROM albums a, users u WHERE u.user_id = a.user_id AND u.first_name='{0}' AND u.last_name='{1}'".format(name[0], name[1]))
				album = cursor.fetchall()
				cursor.execute("SELECT DISTINCT u.user_id FROM albums a, users u WHERE u.user_id = a.user_id AND u.first_name='{0}' AND u.last_name='{1}'".format(name[0],name[1]))
				havealbum = cursor.fetchall()
				cursor.execute("SELECT u.user_id FROM users u WHERE u.first_name='{0}'AND u.last_name='{1}' AND "
							   "u.user_id not in(SELECT DISTINCT a.user_id FROM albums a)".format(name[0],name[1]))
				noalbum = cursor.fetchall()
				return render_template('friends.html',users=user,albums=album,friend=False,noalbum=noalbum,
									   havealbum=havealbum, message='Result from searching friends!')
			else:
				return render_template('friends.html', message="Srrry! Name Doesn't Exist!", unknown=True)
	else:
		return render_template('friends.html', byname=True, message="You can search friends NOW!")

@app.route('/alluser', methods=['GET'])
@flask_login.login_required
def viewall():
	return render_template('friends.html', users=AllUsers(), albums=AllUserAlbums(),friend=False,
						   noalbum=AllUserNoAlbum(), havealbum=AllUserHaveAlbum())

def getUserFriend(uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT u.user_id, u.first_name, u.last_name FROM friends f, users u WHERE f.user_id ='{0}'"
					  "AND f.fri_id = u.user_id ORDER BY f.fri_id".format(uid)):
		return cursor.fetchall()
	else:
		return False

def getUserProfile(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT profile_pic FROM users WHERE user_id = '{0}' AND profile_pic is not NULL".format(uid))
	return cursor.fetchall()

@app.route('/profile')
@flask_login.login_required
def protected():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if not getUserFriend(uid):
		return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
							   message="Here's your profile", friends=False, pic=getUserProfile(uid))
	else:
		return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
							   message="Here's your profile", friends=getUserFriend(uid), pic=getUserProfile(uid))

@app.route('/changeprofile', methods=['GET','POST'])
@flask_login.login_required
def change():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		profile_data = base64.standard_b64encode(imgfile.read())
		cursor = conn.cursor()
		cursor.execute("UPDATE users SET profile_pic='{0}' WHERE user_id = '{1}'".format(profile_data, uid))
		conn.commit()

		if not getUserFriend(uid):
			return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
								   message="Here's your profile", friends=False, change_flag=True, pic=getUserProfile(uid))
		else:
			return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
								   message="Here's your profile", friends=getUserFriend(uid),change_flag=True, pic=getUserProfile(uid))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		if not getUserFriend(uid):
			return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
								   message="Here's your profile", friends=False, change_flag=True, pic=getUserProfile(uid))
		else:
			return render_template('profile.html', name=flask_login.current_user.id, albums=getUsersAlbums(uid),
								   message="Here's your profile", friends=getUserFriend(uid), change_flag=True, pic=getUserProfile(uid))

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#check if the input aid valid
def isAlbumOwned(uid,aid):
	cursor = conn.cursor()
	if cursor.execute("SELECT a.aid FROM users u, albums a WHERE a.user_id = u.user_id AND "
					  "u.user_id='{0}' AND a.aid = '{1}'".format(uid,aid)):
		return True
	else:
		return False

@app.route('/changealbumname', methods=['GET','POST'])
@flask_login.login_required
def modify_album():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		aname = request.form.get('aname')
		aid = request.form.get('aid')
		if isAlbumOwned(uid, aid):
			cursor = conn.cursor()
			cursor.execute("UPDATE albums SET name='{0}' WHERE aid='{1}'".format(aname, aid))
			conn.commit()
			return render_template('profile.html', change_name=False, message='Album Modified!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid), friends=getUserFriend(uid), pic=getUserProfile(uid))
		else:
			return render_template('profile.html', change_name=True, message='Cannot modify album that does not belong to you!',
								   name=flask_login.current_user.id, albums=getUsersAlbums(uid), friends=getUserFriend(uid), pic=getUserProfile(uid))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('profile.html', change_name=True, message="Here's your profile", albums=getUsersAlbums(uid),
							   name=flask_login.current_user.id, friends=getUserFriend(uid), pic=getUserProfile(uid))

@app.route('/delete', methods=['GET','POST'])
@flask_login.login_required
def delete_album():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		aid = request.form.get('aid')
		if isAlbumOwned(uid, aid):
			cursor = conn.cursor()
			cursor.execute("DELETE FROM albums WHERE aid='{0}'".format(aid))
			conn.commit()
			return render_template('profile.html', delete=False, message='Album Deleted!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid), friends=getUserFriend(uid), pic=getUserProfile(uid))
		else:
			return render_template('profile.html', delete=True, message='Cannot delete album that does not belong to you!',
								   name=flask_login.current_user.id, albums=getUsersAlbums(uid), friends=getUserFriend(uid),pic=getUserProfile(uid))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('profile.html', delete=True, message="Ready to let go of your album?", albums=getUsersAlbums(uid),
							   name=flask_login.current_user.id, friends=getUserFriend(uid), pic=getUserProfile(uid))

#create album in the profile page
@app.route('/createalbum1', methods=['GET','POST'])
@flask_login.login_required
def create_album_pro():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		aname = request.form.get('aname')
		cursor = conn.cursor()
		cursor.execute("INSERT INTO albums (name, user_id, date_cr) VALUES ('{0}', '{1}', CURDATE())".format(aname, uid))
		conn.commit()
		return render_template('profile.html', create_tag=False, message='Album created!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid), friends=getUserFriend(uid), pic=getUserProfile(uid))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('profile.html',create_tag = True, message="Here's your profile",albums=getUsersAlbums(uid),
							   name=flask_login.current_user.id, friends=getUserFriend(uid), pic=getUserProfile(uid))

@app.route('/upload', methods=['POST','GET'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		albumid = request.form.get('album_id')
		print (caption)
		photo_data = base64.standard_b64encode(imgfile.read())
		if isAlbumOwned(uid,albumid):
			cursor = conn.cursor()
			cursor.execute("INSERT INTO photo (data, caption, aid) VALUES ('{0}', '{1}', '{2}')".format(photo_data, caption, albumid))
			conn.commit()
			return render_template('profile.html', name=flask_login.current_user.id, message='Photo uploaded!',
							   		albums=getUsersAlbums(uid), photos=getUsersPhotos(uid), pic=getUserProfile(uid))
		else:
			return render_template('upload.html', name=flask_login.current_user.id, message='Invalid Album ID! Please try again!',
								   albums=getUsersAlbums(uid), photos=getUsersPhotos(uid))
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('upload.html', albums = getUsersAlbums(uid))
#end photo uploading code

#create album in the upload page
@app.route('/createalbum', methods=['GET','POST'])
@flask_login.login_required
def create_album():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		aname = request.form.get('aname')
		cursor = conn.cursor()
		cursor.execute("INSERT INTO albums (name, user_id, date_cr) VALUES ('{0}', '{1}', CURDATE())".format(aname, uid))
		conn.commit()
		return render_template('upload.html', create_tag=False, message='Album created!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('upload.html',create_tag = True, name=flask_login.current_user.id)

def getMostTag():
	cursor=conn.cursor()
	cursor.execute("SELECT description, COUNT(*) as c FROM tag_associate GROUP BY description ORDER BY c DESC LIMIT 5")
	return cursor.fetchall()

@app.route('/addtag',methods=['GET','POST'])
@flask_login.login_required
def add_tages():
	if request.method == 'GET':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = getUsersPhotos(uid)
		return render_template('viewphotos.html', addtag = True, photos=getUsersPhotos(uid),tags=getUserPhotoTags(uid),
								havetags=getUserPhotoHaveTags(uid), havecomments=getUserPhotoHaveComments(uid),
								comments=getUserPhotoComments(uid),havelikes=getUserPhotoHaveLikes(uid),
							   likes=getUserPhotoLikes(uid),viewtag=True,view=getMostTag())

	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = request.form.get('pid')
		tname = request.form.get('tagname')
		if isOwnPhoto(uid, pid):
			try:
				cursor = conn.cursor()
				if isTagCreateNeed(tname):
					cursor.execute("INSERT INTO tags VALUES ('{0}')".format(tname))
				cursor.execute("INSERT INTO tag_associate (pid, description) VALUES ('{0}', '{1}')".format(pid, tname))
				conn.commit()
				return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
									   havetags=getUserPhotoHaveTags(uid), havecomments=getUserPhotoHaveComments(uid),
									   comments=getUserPhotoComments(uid),havelikes=getUserPhotoHaveLikes(uid),
									   likes=getUserPhotoLikes(uid), message = 'Succeed! Tag has been added')
			except:
				return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
									   havetags=getUserPhotoHaveTags(uid), havecomments=getUserPhotoHaveComments(uid),
									   comments=getUserPhotoComments(uid), havelikes=getUserPhotoHaveLikes(uid),
									   likes=getUserPhotoLikes(uid), message='Tag already exist!No need to add again!')
		else:
			return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
								   havetags=getUserPhotoHaveTags(uid), addtag = True, havecomments=getUserPhotoHaveComments(uid),
								   comments=getUserPhotoComments(uid), message = 'Not own the photo, please input again',viewtag=True
								   , havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),view=getMostTag())

def getRecommendTag(tag):
	cursor=conn.cursor()
	cursor.execute("SELECT t.description, COUNT(*) as c FROM tag_associate t,"
				   "(SELECT DISTINCT pid FROM photo NATURAL JOIN tag_associate WHERE description = '{0}' OR description = '{1}' "
				   "OR description = '{2}' OR description = '{3}' OR description = '{4}')X WHERE t.pid=X.pid "
				   "AND t.description NOT IN (SELECT DISTINCT description FROM tag_associate "
				   "WHERE description = '{0}' OR description = '{1}' OR description = '{2}' OR description = '{3}' OR description = '{4}') "
				   "GROUP BY t.description ORDER BY c DESC LIMIT 3".format(tag[0], tag[1], tag[2], tag[3], tag[4]))
	return cursor.fetchall()


@app.route('/recommendtag', methods=['POST','GET'])
@flask_login.login_required
def tag_recommand():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		tag=request.form.get('tag')
		tag = tag.split(" ")
		length = len(tag)
		for i in range(1, 6):
			if i > length:
				tag.append("")
		return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
						havetags=getUserPhotoHaveTags(uid), addtag=True, havecomments=getUserPhotoHaveComments(uid),
						comments=getUserPhotoComments(uid), message='Not own the photo, please input again',
						viewtag=True,recom=False, recom_result=getRecommendTag(tag)
						, havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid), view=getMostTag())

	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
						havetags=getUserPhotoHaveTags(uid), addtag=True, havecomments=getUserPhotoHaveComments(uid),
						comments=getUserPhotoComments(uid), message='Get yourself tag recommendation!',
						viewtag=True, recom=True, havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),view=getMostTag())

@app.route('/rmtag',methods=['GET','POST'])
@flask_login.login_required
def remove_tages():
	if request.method == 'GET':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = getUsersPhotos(uid)
		return render_template('viewphotos.html', rmtag = True, photos=getUsersPhotos(uid),tags=getUserPhotoTags(uid),
								havetags=getUserPhotoHaveTags(uid), havecomments=getUserPhotoHaveComments(uid),
								comments=getUserPhotoComments(uid),viewtag=True,havelikes=getUserPhotoHaveLikes(uid),
							   likes=getUserPhotoLikes(uid), view=getMostTag())

	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = request.form.get('pid')
		tname = request.form.get('tagname')
		if isOwnPhoto(uid, pid):
			cursor = conn.cursor()
			cursor.execute("DELETE FROM tag_associate WHERE pid='{0}' AND description='{1}'".format(pid, tname))
			conn.commit()
			return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
								   havetags=getUserPhotoHaveTags(uid), havecomments=getUserPhotoHaveComments(uid),
								   comments=getUserPhotoComments(uid), havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
								   message = 'Succeed! Tag has been removed')
		else:
			return render_template('viewphotos.html', photos=getUsersPhotos(uid), tags=getUserPhotoTags(uid),
								   havetags=getUserPhotoHaveTags(uid), rmtag = True, havecomments=getUserPhotoHaveComments(uid),
								   comments=getUserPhotoComments(uid), message = 'Not own the photo, please input again',viewtag=True
								   , havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),view=getMostTag())


@app.route('/changephoto', methods=['GET','POST'])
@flask_login.login_required
def modify_photo():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		caption = request.form.get('caption')
		pid = request.form.get('pid')
		if isOwnPhoto(uid, pid):
			cursor = conn.cursor()
			cursor.execute("UPDATE photo SET caption='{0}' WHERE pid='{1}'".format(caption, pid))
			conn.commit()
			return render_template('viewphotos.html', change_name=False, message='Photo Modified!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid), friends=getUserFriend(uid),photos=getUsersPhotos(uid),
							   havetags=getUserPhotoHaveTags(uid),
							   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   tags = getUserPhotoTags(uid), view=False)
		else:
			return render_template('viewphotos.html', change_name=True, message='Cannot modify photo that does not belong to you!',
								   name=flask_login.current_user.id, albums=getUsersAlbums(uid), friends=getUserFriend(uid),
								   photos=getUsersPhotos(uid),havetags=getUserPhotoHaveTags(uid),havecomments=getUserPhotoHaveComments(uid),
								   comments=getUserPhotoComments(uid),havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   	tags = getUserPhotoTags(uid), view=False)
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('viewphotos.html', change_name=True, albums=getUsersAlbums(uid),
							   name=flask_login.current_user.id, friends=getUserFriend(uid),photos=getUsersPhotos(uid),
							   havetags=getUserPhotoHaveTags(uid),
							   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   tags = getUserPhotoTags(uid), view=False)

@app.route('/deletephoto', methods=['GET','POST'])
@flask_login.login_required
def delete_photo():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = request.form.get('pid')
		if isOwnPhoto(uid, pid):
			cursor = conn.cursor()
			cursor.execute("DELETE FROM photo WHERE pid='{0}'".format(pid))
			conn.commit()
			return render_template('viewphotos.html', delete=False, message='Photo Deleted!', name=flask_login.current_user.id,
							   albums=getUsersAlbums(uid), friends=getUserFriend(uid),photos=getUsersPhotos(uid),
							   havetags=getUserPhotoHaveTags(uid),havecomments=getUserPhotoHaveComments(uid),
								   comments=getUserPhotoComments(uid),havelikes=getUserPhotoHaveLikes(uid),
								   likes=getUserPhotoLikes(uid),tags = getUserPhotoTags(uid), view=False)
		else:
			return render_template('viewphotos.html', delete=True, message='Cannot delete album that does not belong to you!',
								   name=flask_login.current_user.id, albums=getUsersAlbums(uid), friends=getUserFriend(uid),
								   photos=getUsersPhotos(uid),havetags=getUserPhotoHaveTags(uid),
								   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   		havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   		tags = getUserPhotoTags(uid), view=False)
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('viewphotos.html', delete=True, albums=getUsersAlbums(uid),
							   name=flask_login.current_user.id, friends=getUserFriend(uid), photos=getUsersPhotos(uid),
							   havetags=getUserPhotoHaveTags(uid),
							   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   tags = getUserPhotoTags(uid), view=False)


@app.route('/viewphoto',methods=['GET'])
@flask_login.login_required
def view_my_photo():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('viewphotos.html', photos=getUsersPhotos(uid),havetags=getUserPhotoHaveTags(uid),
						   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
						   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
						   tags = getUserPhotoTags(uid))

def getUsersPhotosbyTag(uid,tag):
	cursor = conn.cursor()
	cursor.execute("SELECT p.data, p.pid, p.caption, a.name, a.aid FROM photo p, albums a,users u, tag_associate t "
				   "WHERE u.user_id = '{0}' AND u.user_id = a.user_id AND p.aid = a.aid AND p.pid =t.pid "
				   "AND t.description = '{1}'".format(uid, tag))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserAllTags(uid):
	cursor=conn.cursor()
	cursor.execute("SELECT DISTINCT t.description FROM tag_associate t, photo p, albums a, users u WHERE u.user_id=a.user_id AND a.aid=p.aid AND t.pid=p.pid AND u.user_id='{0}'".format(uid))
	return cursor.fetchall()


@app.route('/viewmybytag',methods=['GET','POST'])
@flask_login.login_required
def view_my_photo_by_tags():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		tag=request.form.get('tag')
		return render_template('viewphotos.html', photos=getUsersPhotosbyTag(uid,tag),havetags=getUserPhotoHaveTags(uid),
								   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
								   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
								   tags = getUserPhotoTags(uid),bytag=False, view=False, back=True)
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		 ##get all tags that the current user used
		return render_template('viewphotos.html', photos=getUsersPhotos(uid), havetags=getUserPhotoHaveTags(uid),
							   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   tags=getUserPhotoTags(uid), bytag=True, alltags=getUserAllTags(uid))
@app.route('/byme',methods=['GET'])
@flask_login.login_required
def byme():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('viewphotos.html', photos=getUsersPhotos(uid), havetags=getUserPhotoHaveTags(uid),
						   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
						   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
						   tags=getUserPhotoTags(uid), byme =True, bytag=True)

@app.route('/byothers',methods=['GET'])
@flask_login.login_required
def byother():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('viewphotos.html', photos=getUsersPhotos(uid), havetags=getUserPhotoHaveTags(uid),
						   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
						   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
						   tags=getUserPhotoTags(uid), byother =True, bytag=True)

@app.route('/viewotherbytag',methods=['GET','POST'])
@flask_login.login_required
def view_other_photo_by_tags():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		tag=request.form.get('tag')
		cursor=conn.cursor()
		cursor.execute("SELECT p.data, p.pid,p.caption, a.aid,a.name FROM albums a, photo p, tag_associate t "
					   "WHERE t.pid = p.pid AND t.description ='{0}'AND a.aid = p.aid".format(tag))
		photos=cursor.fetchall()
		return render_template('viewotherbytag.html', photos=photos,tags=getPhotoTags(tag),
							   havecomments=getPhotoComment(tag), comments=getPhotoComment(tag),
							   havelikes=getPhotoLikes(tag), likes=getPhotoLikes(tag), view=False, back=True)
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		 ##get all tags that the current user used
		return render_template('viewphotos.html', photos=getUsersPhotos(uid), havetags=getUserPhotoHaveTags(uid),
							   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
							   havelikes=getUserPhotoHaveLikes(uid), likes=getUserPhotoLikes(uid),
							   tags=getUserPhotoTags(uid), bytag=True, alltags=getUserAllTags(uid))

@app.route('/mostpop',methods=['GET'])
@flask_login.login_required
def view_my_photo_most():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('viewphotos.html', photos=getUsersPhotos(uid),havetags=getUserPhotoHaveTags(uid),
						   havecomments=getUserPhotoHaveComments(uid), comments=getUserPhotoComments(uid),
						   tags = getUserPhotoTags(uid), view=getMostTag())

##revised
##get photo information
def getPhotoTags(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT ta.description, ta.pid FROM tag_associate ta, "
				   "(SELECT t.pid FROM tag_associate t,photo p WHERE p.pid = t.pid )X"
				   " WHERE ta.pid =X.pid")
	return cursor.fetchall()

def getPhotoComment(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT c.text, c.pid, u.first_name,u.last_name FROM comment_on c, users u"
				   " WHERE c.user_id = u.user_id")
	return cursor.fetchall()

##Liking photos
def getPhotoLikes(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT l.pid, u.first_name,u.last_name FROM likes l, users u, "
				   "(SELECT t.pid FROM tag_associate t,photo p WHERE p.pid = t.pid )X"
				   " WHERE l.pid =X.pid AND l.user_id = u.user_id")
	return cursor.fetchall()

#search photo by tag name, there could be at most 5 tags being searched
def searchphoto(tag):
	cursor=conn.cursor()
	pidList=[]
	for i in range(n):
		cursor.execute("SELECT pid FROM tag_associate WHERE description = '{0}'".format(tag[i]))
		pids=cursor.fetchall()
		tmp=[]
		for j in pids:
			tmp.append(j[0])
		pidList.append(tmp)

	idset=set(pidList[0]).intersection(*pidList)

	idList=list(idset)
	photos=()
	if idList != []:
		for i in idList:
			cursor.execute("SELECT data, pid, caption FROM photo WHERE pid='{0}'".format(i))
			photo =cursor.fetchall()
			photos += photo
	return photos

def isPhotoExist(pid, tag):
	photos=searchphoto(tag)
	print(pid)
	for i in range(n):
		if cursor.execute("SELECT pid FROM tag_associate WHERE description = '{0}' AND pid ='{1}'".format(tag[i],pid)):
			continue
		else:
			return False

	return True

def getPhotoHaveComments(tag):
	photos=searchphoto(tag)
	pids=[]
	for j in photos:
		pids.append(j[1])
	cursor = conn.cursor()
	have=()
	for i in pids:
		if cursor.execute("SELECT DISTINCT c.pid FROM comment_on c WHERE c.pid= '{0}'".format(i)):
			pid = cursor.fetchall()
			have += pid
	return have

def getPhotoHaveLikes(tag):
	photos=searchphoto(tag)
	pids=[]
	for j in photos:
		pids.append(j[1])
	cursor = conn.cursor()
	have=()
	for i in pids:
		if cursor.execute("SELECT DISTINCT l.pid FROM likes l WHERE l.pid= '{0}'".format(i)):
			pid = cursor.fetchall()
			have += pid
	return have

@app.route('/search', methods=['GET'])
def search():
	cursor=conn.cursor()
	cursor.execute("SELECT DISTINCT description FROM tag_associate")
	all=cursor.fetchall()
	return render_template('search.html',all=all)

@app.route('/mostpop1', methods=['GET'])
def search_most():
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT description FROM tag_associate")
	all = cursor.fetchall()
	return render_template('search.html', view=getMostTag(), all=all)

@app.route('/searchphoto', methods=['GET','POST'])
def searchresult():
	if request.method == 'POST':
		tag = request.form.get('tag')
		tag = tag.split(" ")
		global tag_mark
		global n
		n = len(tag)
		tag_mark = tag
		print(tag[0])
		return render_template('searchphoto.html', photodata=searchphoto(tag_mark),comments=getPhotoComment(tag_mark),
								   havecomments=getPhotoHaveComments(tag_mark), tags=getPhotoTags(tag_mark),havetags=searchphoto(tag_mark),
								   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))
	else:
		return render_template('searchphoto.html', photodata=searchphoto(tag_mark),comments=getPhotoComment(tag_mark),
							   havecomments=getPhotoHaveComments(tag_mark), tags=getPhotoTags(tag_mark),havetags=searchphoto(tag_mark),
							   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))

@app.route('/comment',methods=['GET','POST'])
def make_comment():
	if request.method == 'GET':
		return render_template('searchphoto.html', comment = True, photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
							   havetags=searchphoto(tag_mark),comments=getPhotoComment(tag_mark),havecomments=getPhotoHaveComments(tag_mark),
							   message='You can make your comment NOW',havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))

	if request.method == 'POST':
		try:
			if flask_login.current_user.id:
				uid = getUserIdFromEmail(flask_login.current_user.id)
		except:
			uid = -1
		pid = request.form.get('pid')
		comment = request.form.get('comment')
		if uid != -1:
			if isOwnPhoto(uid, pid):
				return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
									   havetags=searchphoto(tag_mark),comments=getPhotoComment(tag_mark),
									   havecomments=getPhotoHaveComments(tag_mark),havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark),
									   comment=False, message='Hey! Looks like you cannot comment on your own photo')
			else:
				if isPhotoExist(pid, tag_mark):
					cursor = conn.cursor()
					cursor.execute("INSERT INTO comment_on (date, text, user_id, pid) VALUES (CURDATE(), '{0}','{1}','{2}')".format(comment,uid, pid))
					conn.commit()
					return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
										   havetags=searchphoto(tag_mark), message='Succeed! Comment has been added',
										   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark),
										   comments=getPhotoComment(tag_mark),havecomments=getPhotoHaveComments(tag_mark))
				else:
					return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
									   havetags=searchphoto(tag_mark),
									   message='Oops! Looks like the photo is not here!',
									   comments=getPhotoComment(tag_mark), havecomments=getPhotoHaveComments(tag_mark),
									   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))
		else:
			if isPhotoExist(pid, tag_mark):
				cursor = conn.cursor()
				cursor.execute(
					"INSERT INTO comment_on (date, text, user_id, pid) VALUES (CURDATE(), '{0}',0,'{1}')".format(comment, pid))
				conn.commit()
				return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
									   havetags=searchphoto(tag_mark), message='Succeed! Comment has been added',
									   comments=getPhotoComment(tag_mark), havecomments=getPhotoHaveComments(tag_mark),
									   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))
			else:
				return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
									   havetags=searchphoto(tag_mark),
									   message='Oops! Looks like the photo is not here!',
									   comments=getPhotoComment(tag_mark), havecomments=getPhotoHaveComments(tag_mark),
									   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))

def isLiked(uid,pid):
	cursor=conn.cursor()
	if cursor.execute("SELECT pid, user_id FROM likes WHERE pid='{0}' AND user_id='{1}'".format(pid, uid)):
		return True
	else:
		return False

@app.route('/like',methods=['GET','POST'])
@flask_login.login_required
def like():
	if request.method == 'GET':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return render_template('searchphoto.html', like = True, photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
							   havetags=searchphoto(tag_mark),comments=getPhotoComment(tag_mark),havecomments=getPhotoHaveComments(tag_mark),
							   message='It is time to show your appreciation!',havelikes=getPhotoHaveLikes(tag_mark),
							   likes=getPhotoLikes(tag_mark))

	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		pid = request.form.get('pid')
		if isPhotoExist(pid, tag_mark):
			try:
				cursor = conn.cursor()
				cursor.execute("INSERT INTO likes (user_id, pid) VALUES ('{0}','{1}')".format(uid, pid))
				conn.commit()
				return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
										havetags=searchphoto(tag_mark), message='Succeed! Like has been recorded!',
										comments=getPhotoComment(tag_mark),havecomments=getPhotoHaveComments(tag_mark),
									   	havelikes=getPhotoHaveLikes(tag_mark),likes=getPhotoLikes(tag_mark))
			except:
				return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
									   havetags=searchphoto(tag_mark), message='Like already exist!',
									   comments=getPhotoComment(tag_mark), havecomments=getPhotoHaveComments(tag_mark),
									   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))
		else:
			return render_template('searchphoto.html', photodata=searchphoto(tag_mark), tags=getPhotoTags(tag_mark),
								   havetags=searchphoto(tag_mark), message='Oops! Looks like the photo is not here!',
								   comments=getPhotoComment(tag_mark), havecomments=getPhotoHaveComments(tag_mark),
								   havelikes=getPhotoHaveLikes(tag_mark), likes=getPhotoLikes(tag_mark))

def getUser5MostTags(uid):
	cursor=conn.cursor()
	cursor.execute("SELECT description FROM (SELECT t.description, COUNT(*) as c FROM users u, albums a, photo p, tag_associate t WHERE u.user_id='{0}' AND "
				   "t.pid=p.pid AND a.aid=p.aid AND a.user_id=u.user_id GROUP BY t.description ORDER BY c DESC LIMIT 5)X". format(uid))
	usertags=cursor.fetchall()
	tagList=[]
	for i in usertags:
		tagList.append(i[0])
	print(tagList)
	return tagList

def getUser5TagPhotos(taglist):
	score = {}
	tagset= set()
	for i in taglist:
		tagset.add(i)
	cursor=conn.cursor()
	cursor.execute("SELECT description, pid FROM tag_associate")
	alltag=cursor.fetchall()
	for tag in alltag:
		print(tag[1])
		if tag[0] in tagset:
			if score.has_key(tag[1]):
				score[tag[1]]=score[tag[1]]+1
			else:
				score[tag[1]]= 0
				print(score[tag[1]])
		else:
			if score.has_key(tag[1]):
				score[tag[1]]= score[tag[1]]-0.01
			else:
				score[tag[1]] = -0.01
	return score

@app.route('/alsolike', methods=['GET'])
@flask_login.login_required
def also_like():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	tag=getUser5MostTags(uid)
	print(tag)
	score={}
	score=getUser5TagPhotos(tag)
	score_dic=sorted(score.items())
	score_sort=sorted(score.values(),reverse=True)
	print(score_dic)
	print(score_sort)
	cursor=conn.cursor()
	cursor.execute("SELECT pid, data FROM photo WHERE pid NOT IN (SELECT pid FROM photo NATURAL JOIN albums NATURAL JOIN users WHERE user_id = '{0}')".format(uid))
	photos=cursor.fetchall()
	return render_template('alsolike.html',score=score_sort, dictionary=score_dic, photos=photos)

#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run 
	#$ python app.py 
	app.run(port=5000, debug=True)
