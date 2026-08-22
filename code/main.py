from flask import Flask # Flask ist das Web-Framework, das den Webserver bereitstellt.
from routes import register_routes # register_routes lädt alle URL-Routen aus routes.py.
import motor # motor.py wird importiert damit beim Beenden von Flask die GPIO-Pins freigegeben werden.
import camera # camera.py wird importiert damit beim Beenden von Flask die Kamera gestoppt wird.
import led # led.py wird importiert damit beim Beenden von Flask die LEDs ausgeschaltet werden.
import atexit # atexit sorgt dafür dass cleanup() automatisch aufgerufen wird wenn Flask beendet wird.

# Flask-App erstellen
app = Flask(__name__)

# Cache deaktivieren
@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Routen registrieren
register_routes(app)

# Interner Zustand für Cleanup
cleanup_ausgefuehrt = False


# Cleanup bei Beenden
def cleanup_all():
    global cleanup_ausgefuehrt

    if cleanup_ausgefuehrt:
        return

    cleanup_ausgefuehrt = True

    try:
        motor.stop()
    except Exception:
        pass

    try:
        led.led_aus()
    except Exception:
        pass

    try:
        camera.cleanup()
    except Exception:
        pass

    try:
        motor.cleanup()
    except Exception:
        pass

    try:
        led.cleanup()
    except Exception:
        pass


# cleanup_all wird automatisch aufgerufen wenn das Programm beendet wird.
atexit.register(cleanup_all)


# Flask starten
# host='0.0.0.0' bedeutet dass Flask auf alle Netzwerkschnittstellen hört.
# port=5000 ist der Standard-Port für Flask.
# debug=False ist wichtig auf dem Pi, da debug=True einen zweiten Prozess startet der GPIO-Probleme verursacht.
# threaded=True erlaubt gleichzeitige Anfragen, z.B. Kamera-Stream und Fahrbefehle gleichzeitig.
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )