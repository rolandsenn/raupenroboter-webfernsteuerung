from picamera2 import Picamera2 # Picamera2 ist die Python-Library für die Pi-Kamera auf dem Raspberry Pi 5.
from picamera2.encoders import JpegEncoder # JpegEncoder wandelt die Kamerabilder in JPEG-Bilder um.
from picamera2.outputs import FileOutput # FileOutput leitet die JPEG-Bilder an einen Ausgabe-Stream weiter.
import io # io wird verwendet um die JPEG-Bilder im Arbeitsspeicher zwischenzuspeichern.
import threading # threading wird verwendet damit die Kamera parallel zum Rest des Programms läuft.
import time # time wird verwendet, um die FPS des Kamera-Streams zu berechnen.

# Auflösung des MJPEG-Streams.
STREAM_BREITE = 640
STREAM_HOEHE = 480

# Picamera2() erstellt ein Kamera-Objekt.
picam2 = Picamera2()

# Mit create_video_configuration() wird die Kamera für Video-Streaming konfiguriert.
# Die Auflösung wird auf 640x480 Pixel gesetzt.
config = picam2.create_video_configuration(main={"size": (STREAM_BREITE, STREAM_HOEHE)})
picam2.configure(config)

# Interner Zustand der Kamera
# False bedeutet: Kamera ist noch nicht gestartet.
# True bedeutet: Kamera läuft bereits.
kamera_laeuft = False

# Interner Zustand für cleanup()
# False bedeutet: Kamera ist noch nicht geschlossen.
# True bedeutet: Kamera wurde bereits geschlossen.
kamera_geschlossen = False


# FPS-Messung
# Diese Variablen zählen, wie viele Bilder pro Sekunde an Flask gesendet werden.
fps = 0.0
frame_zaehler = 0
letzte_fps_zeit = time.time()


# Ausgabe-Stream
# StreamingOutput speichert das jeweils neueste JPEG-Bild im Arbeitsspeicher.
# threading.Condition() sorgt dafür, dass Flask immer auf das neueste Bild warten kann.
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None # Das aktuellste JPEG-Bild
        self.condition = threading.Condition() # Synchronisation zwischen Kamera und Flask

    def write(self, buf):
        # Wird von picamera2 aufgerufen sobald ein neues Bild bereit ist.
        global fps, frame_zaehler, letzte_fps_zeit

        with self.condition:
            self.frame = buf # Neues Bild speichern
            self.condition.notify_all() # Flask informieren dass ein neues Bild da ist

        # FPS berechnen
        # Bei jedem neuen Bild wird der Zähler erhöht.
        frame_zaehler += 1
        aktuelle_zeit = time.time()
        vergangene_zeit = aktuelle_zeit - letzte_fps_zeit

        # Einmal pro Sekunde wird berechnet, wie viele Bilder pro Sekunde erzeugt wurden.
        if vergangene_zeit >= 1.0:
            fps = frame_zaehler / vergangene_zeit
            frame_zaehler = 0
            letzte_fps_zeit = aktuelle_zeit

        return len(buf)


# Ausgabe-Objekt erstellen
output = StreamingOutput()


# Kamera starten
# Der JpegEncoder wandelt jedes Bild in ein JPEG um und gibt es an output weiter.
def kamera_starten():
    global kamera_laeuft

    if not kamera_laeuft:
        picam2.start_recording(JpegEncoder(), FileOutput(output))
        kamera_laeuft = True


# Aktuelle FPS ausgeben
# Wird von routes.py verwendet, um die FPS auf der Webseite anzuzeigen.
def get_fps():
    return round(fps, 1)


# Aktuelle Stream-Auflösung ausgeben
# Wird von routes.py verwendet, um die Auflösung auf der Webseite anzuzeigen.
def get_aufloesung():
    return f"{STREAM_BREITE}x{STREAM_HOEHE}"


# MJPEG-Stream Generator
# Diese Funktion liefert kontinuierlich neue JPEG-Bilder an Flask.
# Flask gibt sie als Multipart-HTTP-Response an den Browser weiter.
# Der Browser zeigt sie als flüssiges Video an.
def generate_frames():
    kamera_starten()

    while True:
        with output.condition:
            output.condition.wait() # Warten bis ein neues Bild bereit ist
            frame = output.frame # Neustes Bild holen

        if frame is not None:
            # Bild im MJPEG-Format verpacken und an Flask übergeben
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Kamera stoppen
# Wird aufgerufen wenn Flask beendet wird.
def cleanup():
    global kamera_laeuft, kamera_geschlossen

    if kamera_geschlossen:
        return

    if kamera_laeuft:
        picam2.stop_recording()
        kamera_laeuft = False

    picam2.close()
    kamera_geschlossen = True