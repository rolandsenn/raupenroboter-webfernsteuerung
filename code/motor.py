import lgpio # Mit der Python-Library lgpio können die GPIO-Pins des Raspberry Pi 5 gesteuert werden.
import time # time wird für time.sleep() gebraucht, also um den Roboter z.B. 2 Sekunden warten zu lassen.

# GPIO-Setup
h = lgpio.gpiochip_open(0) # Mit gpiochip_open(0) wird der GPIO-Chip des Raspberry Pi 5 geöffnet.

# Pin-Definitionen
# Motor LINKS (BTS7960 #1)
L_RPWM = 13   # Pin 33
L_LPWM = 12   # Pin 32
L_REN  = 23   # Pin 16
L_LEN  = 24   # Pin 18

# Motor RECHTS (BTS7960 #2)
R_RPWM = 19   # Pin 35
R_LPWM = 18   # Pin 12
R_REN  = 5    # Pin 29
R_LEN  = 6    # Pin 31

# Pins als Ausgänge konfigurieren
# Alle Pins werden als Ausgänge gesetzt (der Pi sendet Signale, empfängt nichts). Dann sofort auf LOW gesetzt, damit beim Start kein Motor versehentlich anläuft.
# Die Enable-Pins bleiben beim Start auf LOW, der Motortreiber bleibt deaktiviert bis ein Fahrbefehl kommt.
for pin in [L_RPWM, L_LPWM, L_REN, L_LEN, R_RPWM, R_LPWM, R_REN, R_LEN]:https://github.com/rolandsenn/Maturaarbeit/tree/main
    lgpio.gpio_claim_output(h, pin, 0)

# PWM initialisieren (1000 Hz)
# lgpio.tx_pwm(h, Pin, Frequenz, Duty Cycle) erstellt ein PWM-Signal auf diesem Pin mit 1000 Hz.
# Es werden 4 PWM-Signale verwendet: links-vorwärts, links-rückwärts, rechts-vorwärts und rechts-rückwärts.
# Mit Duty Cycle 0 % liegt kein aktives PWM-Signal an, also bleibt der Motor stehen.
lgpio.tx_pwm(h, L_RPWM, 1000, 0)
lgpio.tx_pwm(h, L_LPWM, 1000, 0)
lgpio.tx_pwm(h, R_RPWM, 1000, 0)
lgpio.tx_pwm(h, R_LPWM, 1000, 0)


# Hilfsfunktion: Geschwindigkeit begrenzen
# Verhindert ungültige Werte wie z.B. vorwaerts(200) oder vorwaerts(-20).
# Der Wert wird immer auf den Bereich 0-100 begrenzt.
def _limit_speed(geschwindigkeit):
    return max(0, min(100, geschwindigkeit))


# Hilfsfunktion: Enable-Pins aktivieren
# BTS7960 fährt nur wenn EN-Pins HIGH sind.
# Diese Funktion wird intern vor jedem Fahrbefehl aufgerufen.
def _enable():
    lgpio.gpio_write(h, L_REN, 1)
    lgpio.gpio_write(h, L_LEN, 1)
    lgpio.gpio_write(h, R_REN, 1)
    lgpio.gpio_write(h, R_LEN, 1)


# Hilfsfunktion: alle PWM auf 0
# Dadurch erhält der BTS7960 kein PWM-Signal mehr, sodass beide Motoren stoppen.
# Zusätzlich werden die Enable-Pins auf LOW gesetzt der BTS7960 wird komplett deaktiviert.
# Diese Funktion wird immer zuerst aufgerufen, bevor ein neuer Fahrbefehl kommt, damit niemals vorwärts und rückwärts gleichzeitig aktiviert sind.
# Da sonst der Motortreiber beschädigt werden könnte.
def stop():
    lgpio.tx_pwm(h, L_RPWM, 1000, 0)
    lgpio.tx_pwm(h, L_LPWM, 1000, 0)
    lgpio.tx_pwm(h, R_RPWM, 1000, 0)
    lgpio.tx_pwm(h, R_LPWM, 1000, 0)
    lgpio.gpio_write(h, L_REN, 0)
    lgpio.gpio_write(h, L_LEN, 0)
    lgpio.gpio_write(h, R_REN, 0)
    lgpio.gpio_write(h, R_LEN, 0)


# Fahrbefehle
def vorwaerts(geschwindigkeit=60):
    # Beide Motoren vorwärts. Geschwindigkeit: 0–100
    geschwindigkeit = _limit_speed(geschwindigkeit)
    stop()
    time.sleep(0.05) # Kurze Pause beim Richtungswechsel zum Schutz des Motortreibers
    _enable()
    lgpio.tx_pwm(h, L_RPWM, 1000, geschwindigkeit)
    lgpio.tx_pwm(h, R_LPWM, 1000, geschwindigkeit)

def rueckwaerts(geschwindigkeit=60):
    # Beide Motoren rückwärts. Geschwindigkeit: 0–100
    geschwindigkeit = _limit_speed(geschwindigkeit)
    stop()
    time.sleep(0.05) # Kurze Pause beim Richtungswechsel zum Schutz des Motortreibers
    _enable()
    lgpio.tx_pwm(h, L_LPWM, 1000, geschwindigkeit)
    lgpio.tx_pwm(h, R_RPWM, 1000, geschwindigkeit)

def links(geschwindigkeit=60):
    # Links drehen: rechter Motor vorwärts, linker rückwärts.
    geschwindigkeit = _limit_speed(geschwindigkeit)
    stop()
    time.sleep(0.05) # Kurze Pause beim Richtungswechsel zum Schutz des Motortreibers
    _enable()
    lgpio.tx_pwm(h, L_LPWM, 1000, geschwindigkeit)
    lgpio.tx_pwm(h, R_LPWM, 1000, geschwindigkeit)

def rechts(geschwindigkeit=60):
    # Rechts drehen: linker Motor vorwärts, rechter rückwärts.
    geschwindigkeit = _limit_speed(geschwindigkeit)
    stop()
    time.sleep(0.05) # Kurze Pause beim Richtungswechsel zum Schutz des Motortreibers
    _enable()
    lgpio.tx_pwm(h, L_RPWM, 1000, geschwindigkeit)
    lgpio.tx_pwm(h, R_RPWM, 1000, geschwindigkeit)


# Aufräumen
# Alle PWM-Signale werden gestoppt und die GPIO-Pins werden wieder freigegeben.
def cleanup():
    stop()
    lgpio.gpiochip_close(h)


# Testprogramm
# Wird nur ausgeführt wenn "motor.py" direkt aufgerufen wird
# Nicht wenn motor.py von Flask importiert wird
# Mit try/except/finally wird eine Sicherheitsstruktur verwendet:
# Egal, ob das Skript normal beendet wird oder ob mit Ctrl+C abgebrochen wird, cleanup() wird immer ausgeführt.
# Dadurch werden die Pins in jedem Fall wieder freigegeben.
if __name__ == "__main__":
    try:
        print("Test: vorwärts 2 Sekunden")
        vorwaerts(60)
        time.sleep(2)

        print("Test: stopp 1 Sekunde")
        stop()
        time.sleep(1)

        print("Test: rückwärts 2 Sekunden")
        rueckwaerts(60)
        time.sleep(2)

        print("Test: stopp 1 Sekunde")
        stop()
        time.sleep(1)

        print("Test: links drehen 1 Sekunde")
        links(60)
        time.sleep(1)

        print("Test: rechts drehen 1 Sekunde")
        rechts(60)
        time.sleep(1)

        print("Test abgeschlossen.")

    except KeyboardInterrupt:
        print("Abbruch")

    finally:
        cleanup()
        print("GPIO freigegeben.")
