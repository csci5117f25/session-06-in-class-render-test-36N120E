# server.py
import os
from flask import Flask, jsonify, request, send_from_directory, Response
from sqlalchemy import text
from geoalchemy2.elements import WKTElement
from db import init_db, db
from models import Place

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    init_db(app)

    with app.app_context():
        db.create_all()
        # spatial index (only need to create once)
        db.session.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_places_geom ON places USING GIST (geom);"
        ))
        db.session.commit()
    
    @app.get("/config.js")
    def config_js():
        # load api keys from environment variables
        m = os.getenv("MAPBOX_KEY", "")
        g = os.getenv("GOOGLE_MAPS_KEY", "")

        def js_str(s): return s.replace("\\", "\\\\").replace("'", "\\'")
        js = f"window.CONFIG={{MAPBOX_KEY:'{js_str(m)}',GOOGLE_MAPS_KEY:'{js_str(g)}'}};"
        return Response(js, mimetype="application/javascript")

    @app.get("/healthz")
    def healthz():
        return "ok"

    # sample data points
    @app.get("/seed")
    def seed():
        count = db.session.execute(text("SELECT COUNT(*) FROM places;")).scalar()
        if count and count > 0:
            return "already seeded"

        demo = [
            # name, category, rating, lng, lat
            ("Blue Cup Cafe", "cafe",   4.6, -93.2650, 44.9778),
            ("Lake Park",     "park",   4.5, -93.2612, 44.9801),
            ("City Museum",   "museum", 4.7, -93.2685, 44.9762),
            ("Bean Bar",      "cafe",   4.2, -93.2721, 44.9757),
            ("Riverside",     "park",   4.4, -93.2579, 44.9719),
            ("Art House",     "museum", 4.8, -93.2592, 44.9830),
        ]
        for name, cat, rating, lng, lat in demo:
            p = Place(
                name=name, category=cat, rating=rating,
                geom=WKTElement(f"POINT({lng} {lat})", srid=4326)
            )
            db.session.add(p)
        db.session.commit()
        return "seeded"

    # GeoJSON API：/api/places?bbox=minx,miny,maxx,maxy&q=...&category=cafe,park&limit=200
    @app.get("/api/places")
    def api_places():
        bbox = request.args.get("bbox")         # minx,miny,maxx,maxy (WGS84)
        q    = request.args.get("q", "").strip()
        cats = request.args.get("category", "")
        limit= max(1, min(int(request.args.get("limit", 200)), 1000))

        where = ["TRUE"]
        params = {"limit": limit}

        if bbox:
            minx, miny, maxx, maxy = map(float, bbox.split(","))
            where.append("ST_Intersects(geom, ST_MakeEnvelope(:minx,:miny,:maxx,:maxy,4326))")
            params.update(dict(minx=minx, miny=miny, maxx=maxx, maxy=maxy))

        if q:
            where.append("name ILIKE :q")
            params["q"] = f"%{q}%"

        if cats:
            arr = [c.strip() for c in cats.split(",") if c.strip()]
            if arr:
                where.append("category = ANY(:cats)")
                params["cats"] = arr

        sql = f"""
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type','Feature',
              'geometry', ST_AsGeoJSON(geom)::jsonb,
              'properties', jsonb_build_object(
                'id', id, 'name', name, 'category', category, 'rating', rating
              )
            )
          ), '[]'::jsonb)
        )
        FROM (
          SELECT id, name, category, rating, geom
          FROM places
          WHERE {' AND '.join(where)}
          ORDER BY rating DESC, id ASC
          LIMIT :limit
        ) t;
        """
        fc = db.session.execute(text(sql), params).scalar()
        return jsonify(fc)

    # nearby /api/nearby?lng=-93.26&lat=44.98&radius_m=10000
    @app.get("/api/nearby")
    def api_nearby():
        lng = float(request.args["lng"]); lat = float(request.args["lat"])
        radius = float(request.args.get("radius_m", 10000))
        sql = """
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', jsonb_agg(
            jsonb_build_object(
              'type','Feature',
              'geometry', ST_AsGeoJSON(geom)::jsonb,
              'properties', jsonb_build_object(
                'id', id, 'name', name, 'category', category, 'rating', rating,
                'distance_m', round(ST_Distance(geom::geography, ST_SetSRID(ST_Point(:lng,:lat),4326)::geography))
              )
            )
          )
        )
        FROM (
          SELECT * FROM places
          WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_Point(:lng,:lat),4326)::geography, :radius)
          ORDER BY ST_Distance(geom::geography, ST_SetSRID(ST_Point(:lng,:lat),4326)::geography)
          LIMIT 500
        ) t;
        """
        fc = db.session.execute(text(sql), {"lng": lng, "lat": lat, "radius": radius}).scalar()
        return jsonify(fc or {"type":"FeatureCollection","features":[]})

    @app.get("/")
    def root():
        return send_from_directory(app.static_folder, "index_leaflet.html")

    @app.get("/mapbox")
    def mapbox():
        return send_from_directory(app.static_folder, "index_mapbox.html")


    @app.get("/google")
    def google():
        return send_from_directory(app.static_folder, "index_google.html")
    
    @app.get("/mb_changestyle")
    def mb_changestyle():
        return send_from_directory(app.static_folder, "mb_changestyle.html")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(port=8000, debug=True)



# import os
# from flask import Flask, jsonify, render_template
# from sqlalchemy import func, cast
# from geoalchemy2 import Geography
# from geoalchemy2.elements import WKTElement

# from db import init_db, db
# from models import Park

# def create_app():
#     app = Flask(__name__)
#     init_db(app)

#     with app.app_context():
#         db.create_all()

#     @app.route("/")
#     def index():
#         return "Hello from Render + PostGIS!"
    
#     @app.route('/hello')
#     def hello(name=None):
#         return render_template('hello.html', name=name)

#     @app.route("/add_demo")
#     def add_demo():
#         # insert demo polygon（WKT）
#         poly_wkt = (
#             "POLYGON((-93.27 44.97,-93.26 44.97,-93.26 44.98,"
#             "-93.27 44.98,-93.27 44.97))"
#         )
#         geom = WKTElement(poly_wkt, srid=4326)
#         p = Park(name="Demo Park", geom=geom)
#         db.session.add(p)
#         db.session.commit()
#         return "inserted"

#     @app.route("/area")
#     def area():
#         rows = (
#             db.session.query(
#                 Park.name,
#                 func.ST_Area(cast(Park.geom, Geography)).label("area_m2"),
#             )
#             .all()
#         )
#         return jsonify([{"name": n, "area_m2": float(a)} for n, a in rows])

#     @app.route("/healthz")
#     def healthz():
#         return "ok"

#     return app

# app = create_app()

