from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Item
app = Flask(__name__)


engine = create_engine('sqlite:///catalogDB.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

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

    session.add(item1)

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

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)




