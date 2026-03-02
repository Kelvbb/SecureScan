from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/respirer")
def respirer():
    """Health-check endpoint — confirms the application is alive and breathing."""
    return jsonify({"status": "ok", "message": "SecureScan is running"})


if __name__ == "__main__":
    import os
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
