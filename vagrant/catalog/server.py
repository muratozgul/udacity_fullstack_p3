from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Item

app = Flask(__name__)

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
    #restaurant = session.query(Restaurant).first()
    #items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    categories = session.query(Category)
    items = session.query(Item)
    squares = [i*i for i in range(10)]
    return render_template('index.html', categories= categories, items=items)


@app.route('/category/<int:category_id>')
def category(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return render_template('category_show.html', category=category, items=items)

    
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)




