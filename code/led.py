import lgpio # Mit der Python-Library lgpio können die GPIO-Pins des Raspberry Pi 5 gesteuert werden.

# GPIO-Setup
# Mit gpiochip_open(0) wird der GPIO-Chip des Raspberry Pi 5 geöffnet.
# led.py verwendet einen eigenen Chip-Handle.
h = lgpio.gpiochip_open(0)

# Pin-Definition
# Beide LEDs sind parallel an GPIO-Pin 21 angeschlossen, jede mit einem eigenen 330-Ω-Vorwiderstand.
LED_PIN = 21  # Pin 40

# Interner Zustand der LED
# False bedeutet: LED aus
# True bedeutet: LED an
led_status = False

# Pin als Ausgang konfigurieren
# Der Pin wird als Ausgang gesetzt und sofort auf LOW gesetzt, damit die LEDs beim Start aus sind.
lgpio.gpio_claim_output(h, LED_PIN, 0)


# LED einschalten
# Der GPIO-Pin wird auf HIGH (3.3 V) gesetzt, dadurch leuchten beide LEDs.
def led_an():
    global led_status
    lgpio.gpio_write(h, LED_PIN, 1)
    led_status = True


# LED ausschalten
# Der GPIO-Pin wird auf LOW (0 V) gesetzt, dadurch erlöschen beide LEDs.
def led_aus():
    global led_status
    lgpio.gpio_write(h, LED_PIN, 0)
    led_status = False


# LED umschalten
# Falls die LED gerade an ist, wird sie ausgeschaltet und umgekehrt.
def led_toggle():
    if led_status:
        led_aus()
    else:
        led_an()


# Aufräumen
# Der GPIO-Pin wird wieder freigegeben.
def cleanup():
    global h

    if h is not None:
        led_aus()
        lgpio.gpiochip_close(h)
        h = None