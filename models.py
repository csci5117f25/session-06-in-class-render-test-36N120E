# models.py
from db import db
from geoalchemy2 import Geometry

class Place(db.Model):
    __tablename__ = "places"
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(128))
    category = db.Column(db.String(64))  # e.g. cafe/park/museum
    rating   = db.Column(db.Float)       # 1.0-5.0
    # WGS84 点
    geom     = db.Column(Geometry(geometry_type="POINT", srid=4326))
    

# from db import db
# from geoalchemy2 import Geometry

# class Park(db.Model):
#     __tablename__ = "parks"
#     id   = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(255))
#     # SRID=4326 的多边形
#     geom = db.Column(Geometry(geometry_type="POLYGON", srid=4326))
