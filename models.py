# models.py
from db import db
from geoalchemy2 import Geometry

class Park(db.Model):
    __tablename__ = "parks"
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    # SRID=4326 的多边形
    geom = db.Column(Geometry(geometry_type="POLYGON", srid=4326))
