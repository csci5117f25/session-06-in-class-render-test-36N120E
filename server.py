from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello from Render!"

@app.route('/app')
def hello(name=None):
    return render_template('hello.html', name=name)


# server.py
import os
from flask import Flask, jsonify
from sqlalchemy import func, cast
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement

from db import init_db, db
from models import Park

def create_app():
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return "Hello from Render + PostGIS!"
    
    @app.route('/hello')
    def hello(name=None):
        return render_template('hello.html', name=name)

    @app.route("/add_demo")
    def add_demo():
        # insert demo polygon（WKT）
        poly_wkt = (
            "POLYGON((-93.27 44.97,-93.26 44.97,-93.26 44.98,"
            "-93.27 44.98,-93.27 44.97))"
        )
        geom = WKTElement(poly_wkt, srid=4326)
        p = Park(name="Demo Park", geom=geom)
        db.session.add(p)
        db.session.commit()
        return "inserted"

    @app.route("/area")
    def area():
        rows = (
            db.session.query(
                Park.name,
                func.ST_Area(cast(Park.geom, Geography)).label("area_m2"),
            )
            .all()
        )
        return jsonify([{"name": n, "area_m2": float(a)} for n, a in rows])

    @app.route("/healthz")
    def healthz():
        return "ok"

    return app

app = create_app()

