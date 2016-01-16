from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Item, User

from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "mozgul_udacity_fs_p3"

engine = create_engine('sqlite:///catalogDB.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

#populate db with seed data
#(deletes previous rows)
@app.route('/db/seed')
def db_populate_from_seed():
    session.query(Category).delete()

    category1 = Category(name="Bowling")
    category2 = Category(name="Tennis")

    session.add(category1)
    session.add(category2)
    session.flush()
    session.refresh(category1)
    session.refresh(category2)

    item1 = Item(name="HeavyBall", description="Bowling Ball", category_id=category1.id)
    item2 = Item(name="Racket", description="Medium Size Racket", category_id=category2.id)

    session.add(item1)
    session.add(item2)

    try:
        session.commit()
    except Exception as e:
        return "Error trying seed populate db"

    return "db re-populated with seed"


@app.route('/')
def landing():
    categories = session.query(Category)
    items = session.query(Item)

    if 'username' not in login_session:
        return render_template('index.html', categories= categories, items=items, isLoggedIn=False)
    else:
        return render_template('index.html', categories= categories, items=items, isLoggedIn=True)


@app.route('/category/<int:category_id>')
def category(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()

    if 'username' not in login_session:
        return render_template('category_show.html', category=category, items=items, isLoggedIn=False)
    else:
        return render_template('category_show.html', category=category, items=items, isLoggedIn=True)


@app.route('/category/<int:category_id>/json')
def jsonifyCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    
    itemList = [i.serialize for i in items]
    sCategory = category.serialize
    sCategory["items"] = itemList
    return jsonify(category=sCategory)


@app.route('/item/<int:item_id>')
def item(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    if 'username' not in login_session:
        return render_template('item_show.html', item=item, isLoggedIn=False)
    else:
        return render_template('item_show.html', item=item, isLoggedIn=True)


@app.route('/category/<int:category_id>/new', methods=['GET', 'POST'])
def newItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')

    if request.method == 'POST':
        newItem = Item(
            name=request.form['name'], 
            description=request.form['description'], 
            category_id=category_id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('category', category_id=category_id))
    else :
        return render_template('item_new.html', category_id=category_id)


@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id):
    if 'username' not in login_session:
        return redirect('/login')

    item = session.query(Item).filter_by(id=item_id).one()

    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        session.commit()
        return redirect(url_for('item', item_id=item_id))
    else :
        return render_template('item_edit.html', item=item)


@app.route('/category/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(item_id):
    if 'username' not in login_session:
        return redirect('/login')

    item = session.query(Item).filter_by(id=item_id).one()
    
    if request.method == 'POST':
        category_id = item.category.id
        session.delete(item)
        session.commit()
        return redirect(url_for('category', category_id=category_id))
    else :
        return render_template('item_delete.html', item=item)
        

@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout')
def logout():
    gdisconnect()
    del login_session['gplus_id']
    del login_session['access_token']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['user_id']
    return redirect(url_for('landing'))


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    #stored_credentials = login_session.get('credentials')
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    #login_session['credentials'] = credentials
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    #params = {'access_token': credentials.access_token, 'alt': 'json'}
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    #flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    #credentials = login_session.get('credentials')
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)




















