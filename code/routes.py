from flask import Response, jsonify, render_template # Flask-Funktionen für HTTP-Antworten und JSON.
from datetime import datetime # datetime wird verwendet, um die aktuelle Uhrzeit des Raspberry Pi auszugeben.
import threading # threading wird verwendet, damit nicht mehrere Fahrbefehle gleichzeitig ausgeführt werden.
import time # time wird für den serverseitigen Heartbeat-Watchdog verwendet.
import subprocess # subprocess wird verwendet, um den Raspberry Pi herunterzufahren.

import motor # motor.py wird importiert um die Fahrbefehle aufzurufen.
import led # led.py wird importiert um die LEDs zu steuern.
import camera # camera.py wird importiert um den MJPEG-Stream bereitzustellen.


# Sperre für Motorbefehle
# Dadurch wird verhindert, dass mehrere Fahrbefehle gleichzeitig an die Motoren gesendet werden.
motor_lock = threading.Lock()

# Sperre für den Fahrzustand
# Dadurch wird verhindert, dass Heartbeat und Fahrbefehle gleichzeitig denselben Zustand verändern.
state_lock = threading.Lock()

# Aktuelle Geschwindigkeit
# Diese Variable speichert die Geschwindigkeit, die über /geschwindigkeit/<wert> gesetzt wird.
aktuelle_geschwindigkeit = 60

# Heartbeat / Watchdog
# Der Browser sendet während dem Fahren regelmässig erneut den Fahrbefehl.
# Wenn länger als WATCHDOG_TIMEOUT Sekunden kein Fahrbefehl mehr ankommt, stoppt der Server den Roboter automatisch.
letzter_fahrbefehl = 0.0
fahrt_aktiv = False


# Der Roboter stoppt bei Verbindungsabbruch, aber nicht sofort wegen kleiner Internet-Schwankungen.
WATCHDOG_TIMEOUT = 1.2

# Der Watchdog prüft alle 100 ms, ob der letzte Fahrbefehl zu lange her ist.
WATCHDOG_CHECK_INTERVAL = 0.1

# Damit der Watchdog-Thread nur einmal gestartet wird.
watchdog_gestartet = False


# Hilfsfunktion: Geschwindigkeit begrenzen
# Der Wert wird immer auf den Bereich 0–100 begrenzt.
def begrenze_geschwindigkeit(wert):
    return max(0, min(100, wert))


# Hilfsfunktion: Zeitpunkt des letzten Fahrbefehls aktualisieren
# Diese Funktion wird bei jedem Fahrbefehl aufgerufen.
def heartbeat_aktualisieren():
    global letzter_fahrbefehl, fahrt_aktiv

    with state_lock:
        letzter_fahrbefehl = time.monotonic()
        fahrt_aktiv = True


# Hilfsfunktion: Fahrzustand beenden
# Diese Funktion wird verwendet, wenn der Roboter bewusst gestoppt wird.
def fahrt_beenden():
    global fahrt_aktiv

    with state_lock:
        fahrt_aktiv = False


# Watchdog-Funktion
# Diese Funktion läuft dauerhaft im Hintergrund.
# Wenn zu lange kein Fahrbefehl mehr vom Browser angekommen ist, wird motor.stop() ausgeführt.
def watchdog_loop():
    global fahrt_aktiv

    while True:
        time.sleep(WATCHDOG_CHECK_INTERVAL)

        soll_stoppen = False

        with state_lock:
            if fahrt_aktiv:
                vergangene_zeit = time.monotonic() - letzter_fahrbefehl

                if vergangene_zeit > WATCHDOG_TIMEOUT:
                    fahrt_aktiv = False
                    soll_stoppen = True

        if soll_stoppen:
            with motor_lock:
                motor.stop()


# Watchdog starten
# Der Thread läuft als daemon=True, damit er beim Beenden des Programms automatisch mit beendet wird.
def starte_watchdog():
    global watchdog_gestartet

    if not watchdog_gestartet:
        thread = threading.Thread(target=watchdog_loop, daemon=True)
        thread.start()
        watchdog_gestartet = True


# Fahrbefehl ausführen
# Diese Funktion bündelt alle Richtungen an einer Stelle.
def fuehre_fahrbefehl_aus(richtung):
    if richtung == "vorwaerts":
        motor.vorwaerts(aktuelle_geschwindigkeit)

    elif richtung == "rueckwaerts":
        motor.rueckwaerts(aktuelle_geschwindigkeit)

    elif richtung == "links":
        motor.links(aktuelle_geschwindigkeit)

    elif richtung == "rechts":
        motor.rechts(aktuelle_geschwindigkeit)

    else:
        return False

    return True


def register_routes(app):

    # Watchdog beim Registrieren der Routen starten
    starte_watchdog()


    # Startseite
    # Wenn der Browser die Hauptadresse aufruft, wird index.html geladen.
    @app.route("/")
    def index():
        return render_template("index.html")


    # Fahrbefehle
    @app.route("/fahren/<richtung>", methods=["POST"])
    def fahren(richtung):
        if richtung == "stop":
            fahrt_beenden()

            with motor_lock:
                motor.stop()

            return jsonify({
                "status": "ok",
                "befehl": "stop"
            })

        if richtung not in ["vorwaerts", "rueckwaerts", "links", "rechts"]:
            return jsonify({
                "status": "error",
                "message": "Unbekannte Richtung"
            }), 400

        heartbeat_aktualisieren()

        with motor_lock:
            erfolgreich = fuehre_fahrbefehl_aus(richtung)

        if not erfolgreich:
            return jsonify({
                "status": "error",
                "message": "Fahrbefehl konnte nicht ausgeführt werden"
            }), 400

        return jsonify({
            "status": "ok",
            "befehl": richtung,
            "geschwindigkeit": aktuelle_geschwindigkeit
        })


    # Geschwindigkeit setzen
    @app.route("/geschwindigkeit/<int:wert>", methods=["POST"])
    def geschwindigkeit(wert):
        global aktuelle_geschwindigkeit

        aktuelle_geschwindigkeit = begrenze_geschwindigkeit(wert)

        return jsonify({
            "status": "ok",
            "geschwindigkeit": aktuelle_geschwindigkeit
        })


    # LED-Steuerung
    @app.route("/led/an", methods=["POST"])
    def led_an():
        led.led_an()

        return jsonify({
            "status": "ok",
            "led": "an"
        })


    @app.route("/led/aus", methods=["POST"])
    def led_aus():
        led.led_aus()

        return jsonify({
            "status": "ok",
            "led": "aus"
        })


    @app.route("/led/toggle", methods=["POST"])
    def led_toggle():
        led.led_toggle()

        return jsonify({
            "status": "ok",
            "led": "toggle"
        })


    # MJPEG-Stream
    @app.route("/video", methods=["GET"])
    def video():
        return Response(
            camera.generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame"
        )


    # Statusdaten für die Webseite
    @app.route("/api/status", methods=["GET"])
    def api_status():
        return jsonify({
            "zeit": datetime.now().strftime("%H:%M:%S"),
            "aufloesung": camera.get_aufloesung(),
            "fps": camera.get_fps()
        })


    # Ping-Test
    @app.route("/api/ping", methods=["GET"])
    def api_ping():
        return jsonify({
            "status": "ok"
        })


    # Raspberry Pi herunterfahren
    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        try:
            fahrt_beenden()

            with motor_lock:
                motor.stop()

            led.led_aus()

            subprocess.Popen(["sudo", "/usr/sbin/shutdown", "now"])

            return jsonify({
                "status": "ok",
                "message": "Raspberry Pi fährt herunter"
            })

        except Exception as fehler:
            return jsonify({
                "status": "error",
                "message": str(fehler)
            }), 500