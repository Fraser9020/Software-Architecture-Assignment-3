"""Start the whole app with the pickup and payment pages added.

Run from the App folder:  python run_pickup.py
Then open http://127.0.0.1:5000/pickup
(Fraser's app.py is not changed.)
"""
from app import app
from pickup_data import load_test_data
from pickup_routes import pickup_bp

app.register_blueprint(pickup_bp)

if __name__ == "__main__":
    load_test_data()
    app.run(debug=True)
