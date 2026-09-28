from machine import UART, Pin, I2C
import time

import constants
from micropyGPS import MicropyGPS
import sds011
from scd4Pressure import SCD4X
from bme680 import BME680_I2C
import ssd1306


# ===== ALGEMENE INSTELLINGEN =====
# De sensoren worden om de 10 seconden uitgelezen. Eenmaal per minuut wordt
# de mediaan van de geldige meetwaarden naar DATA geschreven.
MEETINTERVAL_MS = 10000
OPSLAGINTERVAL_MS = 60000
# De GPS-tijd zelf blijft altijd UTC en wordt zo naar DATA geschreven.
# Pas voor weergave op het OLED-scherm aan voor België en Oostenrijk:
# UTC+2 in zomertijd, UTC+1 in wintertijd.
UTC_OFFSET_UREN = 2

# ===== GPS =====
# MicropyGPS verwerkt de NMEA-gegevens van de GPS-module.
# De globale GPS-waarden bewaren steeds de laatst ontvangen geldige informatie.
my_gps = MicropyGPS()
gps_serial = UART(2, baudrate=9600, tx=17, rx=16)

tijdGPS = 0
lengtegraad = 0
breedtegraad = 0
hoogte = 0


# ===== I2C EN SENSOREN =====
# De BME680, SCD4X en het OLED-scherm delen dezelfde I2C-bus
# op pin 22 (SCL) en pin 21 (SDA).
i2c = I2C(scl=Pin(22), sda=Pin(21))

# Sensorobjecten starten als None. Elke sensor wordt afzonderlijk geïnitialiseerd.
# Als één sensor bij het opstarten niet reageert, blijven de andere onderdelen werken.
sensor = None
bme = None
uartDust = None
dust_sensor = None
oled = None

# Het SSD1306 OLED-scherm heeft een resolutie van 128 x 64 pixels.
oled_width = 128
oled_height = 64


def init_scd():
    global sensor

    try:
        nieuwe_sensor = SCD4X(i2c)
        nieuwe_sensor.start_periodic_measurement()
        time.sleep(5)
        sensor = nieuwe_sensor
        print("SCD4X gestart")
        return True

    except Exception as e:
        sensor = None
        print("SCD4X-opstartfout:", e)
        return False


def init_bme():
    global bme

    try:
        bme = BME680_I2C(i2c=i2c)
        print("BME680 gestart")
        return True

    except Exception as e:
        bme = None
        print("BME680-opstartfout:", e)
        return False


def init_dust():
    global uartDust, dust_sensor

    try:
        nieuwe_uart = UART(1, 9600)
        nieuwe_uart.init(9600, rx=26, tx=25, timeout_char=2)
        nieuwe_dust_sensor = sds011.SDS011(nieuwe_uart)

        uartDust = nieuwe_uart
        dust_sensor = nieuwe_dust_sensor

        print("SDS011 gestart")
        return True

    except Exception as e:
        uartDust = None
        dust_sensor = None
        print("SDS011-opstartfout:", e)
        return False


def init_oled():
    global oled

    try:
        oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
        print("OLED gestart")
        return True

    except Exception as e:
        oled = None
        print("OLED-opstartfout:", e)
        return False


# ===== ACTUELE SENSORWAARDEN =====
# Deze variabelen bevatten telkens de meest recente geldige losse sensormeting.
# Het OLED-scherm toont deze actuele waarden; DATA krijgt later de mediaan per minuut.
co2 = 0
temp = 0
hum = 0
pres = 0
gas = 0
PM25 = 0
PM10 = 0


# ===== GPS UITLEZEN =====
# Deze functie verwerkt alle GPS-gegevens die op dat moment in de UART-buffer staan.
# tijdGPS wordt hier opgeslagen in het formaat YYYY-MM-DDTHH:MM (bijv. 2026-09-28T23:00).
def meetGPS():
    global tijdGPS, breedtegraad, lengtegraad, hoogte

    nieuwe_fix = False

    try:
        while gps_serial.any():
            data = gps_serial.read()

            if data is None:
                break

            for byte in data:
                stat = my_gps.update(chr(byte))

                if stat is not None:
                    # Converteer GPS-datum en tijd naar het gewenste formaat: 2026-09-28T23:00
                    jaar_val = int(my_gps.date[2]) + 2000
                    maand_val = int(my_gps.date[1])
                    dag_val = int(my_gps.date[0])
                    uur_val = int(my_gps.timestamp[0])
                    minuut_val = int(my_gps.timestamp[1])

                    tijdGPS = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}".format(
                        jaar_val, maand_val, dag_val, uur_val, minuut_val
                    )

                    # Positie en hoogte alleen overschrijven bij een geldige GGA-fix.
                    try:
                        if stat in ("GPGGA", "GLGGA", "GNGGA") and my_gps.fix_stat > 0:
                            breedtegraad = my_gps.latitude_string()
                            lengtegraad = my_gps.longitude_string()
                            hoogte = my_gps.altitude
                            nieuwe_fix = True
                    except Exception:
                        pass

    except Exception as e:
        print("GPS-fout:", e)

    return nieuwe_fix


# ===== BME680 UITLEZEN =====
def readBME():
    global temp, hum, pres, gas

    if bme is None and not init_bme():
        return False

    try:
        # Eventuele kalibratiewaarden (y = a * x + b)
        # Voor een eventuele hercalibratie moeten de a waarde 1.0 worden en de b waarde 0.0, hierna pas kan je de nieuwe
        # calibratiegegevens meten!
        a_temp, b_temp = 1.0, 0.0
        a_hum, b_hum   = 1.0, 0.0
        a_pres, b_pres = 1.0, 0.0

        nieuwe_temp = (bme.temperature * a_temp) + b_temp
        nieuwe_hum = (bme.humidity * a_hum) + b_hum
        nieuwe_pres = (bme.pressure * a_pres) + b_pres
        nieuwe_gas = bme.gas / 1000

        temp = nieuwe_temp
        hum = nieuwe_hum
        pres = nieuwe_pres
        gas = nieuwe_gas

        return True

    except Exception as e:
        print("BME680-fout:", e)
        return False


# ===== SCD4X UITLEZEN =====
def readSCD():
    global co2

    if sensor is None and not init_scd():
        return False

    try:
        nieuwe_co2 = sensor.co2
        co2 = nieuwe_co2
        return True

    except Exception as e:
        print("SCD4X-fout:", e)
        return False


# ===== SDS011 UITLEZEN =====
def readDust():
    global PM25, PM10

    if dust_sensor is None and not init_dust():
        return False

    try:
        dust_sensor.read()
        nieuwe_PM25 = dust_sensor.pm25
        nieuwe_PM10 = dust_sensor.pm10

        PM25 = nieuwe_PM25
        PM10 = nieuwe_PM10

        return True

    except Exception as e:
        print("SDS011-fout:", e)
        return False


# ===== MEDIAAN =====
def median(waarden):
    n = len(waarden)

    if n == 0:
        return 0

    gesorteerd = sorted(waarden)

    if n % 2 == 0:
        midden1 = gesorteerd[n // 2 - 1]
        midden2 = gesorteerd[n // 2]
        mediaan = (midden1 + midden2) / 2
    else:
        mediaan = gesorteerd[n // 2]

    return round(mediaan, 2)


# ===== DATUMHULPFUNCTIES =====
def is_schrikkeljaar(jaar):
    return jaar % 4 == 0 and (jaar % 100 != 0 or jaar % 400 == 0)


def dagen_in_maand(maand, jaar):
    dagen = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    if is_schrikkeljaar(jaar):
        dagen[1] = 29

    return dagen[maand - 1]


# ===== GPS-TIJD VOOR HET OLED (Aangepast op YYYY-MM-DDTHH:MM) =====
def gps_tekst_lokaal():
    if tijdGPS == 0 or tijdGPS == "0":
        return "Datum:--/--/----", "Tijd: --:--"

    try:
        # Splits het nieuwe formaat "2026-09-28T23:00"
        s_datum, s_tijd = str(tijdGPS).split("T")
        jaar_str, maand_str, dag_str = s_datum.split("-")
        uur_str, minuut_str = s_tijd.split(":")

        jaar = int(jaar_str)
        maand = int(maand_str)
        dag = int(dag_str)
        uur = int(uur_str)
        minuut = int(minuut_str)

        if maand < 1 or maand > 12 or dag < 1:
            return "Datum:--/--/----", "Tijd: --:--"

        # Alleen de schermweergave wordt naar de plaatselijke tijd omgerekend.
        uur += UTC_OFFSET_UREN

        while uur >= 24:
            uur -= 24
            dag += 1

            if dag > dagen_in_maand(maand, jaar):
                dag = 1
                maand += 1

                if maand > 12:
                    maand = 1
                    jaar += 1

        datumTekst = "Datum:{:02d}/{:02d}/{:04d}".format(dag, maand, jaar)
        tijdTekst = "Tijd: {:02d}:{:02d}".format(uur, minuut)

        return datumTekst, tijdTekst

    except Exception:
        return "Datum:--/--/----", "Tijd: --:--"


# ===== OLED-SCHERMEN =====
def toon_scherm(schermnummer, laatste_opslag, volgende_opslag):
    if oled is None and not init_oled():
        return

    nu = time.ticks_ms()

    tijd_sinds = int(time.ticks_diff(nu, laatste_opslag) / 1000)
    tijd_tot = int(time.ticks_diff(volgende_opslag, nu) / 1000)

    if tijd_sinds < 0:
        tijd_sinds = 0
    if tijd_tot < 0:
        tijd_tot = 0

    datumTekst, tijdTekst = gps_tekst_lokaal()

    scherm1 = [
        "Hoogte: {} m".format(round(hoogte)),
        "Ldruk: {} hPa".format(round(pres)),
        "Temp: {} C".format(round(temp)),
        "RH: {} %".format(round(hum))
    ]

    scherm2 = [
        "CO2:  {} ppm".format(round(co2)),
        "PM25: {} mcg/m3".format(round(PM25)),
        "PM10: {} mcg/m3".format(round(PM10)),
        "RVOC: {} kOhm".format(round(gas))
    ]

    scherm3 = [
        datumTekst,
        tijdTekst,
        "Tijd< {} s".format(tijd_sinds),
        "Tijd> {} s".format(tijd_tot)
    ]

    schermen = [scherm1, scherm2, scherm3]
    gekozen_scherm = schermen[schermnummer]

    try:
        oled.fill(0)

        for lijnnr in range(4):
            oled.text(gekozen_scherm[lijnnr], 0, lijnnr * 16)

        oled.show()

    except Exception as e:
        print("OLED-fout:", e)


# ===== DATA WEGSCHRIJVEN =====
def schrijf_data(
    co2List,
    pressList,
    tempList,
    humList,
    gasList,
    PM25List,
    PM10List,
    hoogteList
):
    tijd = time.ticks_ms() / 1000 / 60

    if len(hoogteList) > 0:
        lengtegraad_data = lengtegraad
        breedtegraad_data = breedtegraad
        hoogte_data = median(hoogteList)
    else:
        lengtegraad_data = 0
        breedtegraad_data = 0
        hoogte_data = 0

    with open("DATA", "a") as fdata:
        fdata.write(
            str(round(tijd, 2)) + "," +
            str(median(co2List)) + "," +
            str(median(tempList)) + "," +
            str(median(humList)) + "," +
            str(median(pressList)) + "," +
            str(median(gasList)) + "," +
            str(median(PM25List)) + "," +
            str(median(PM10List)) + "," +
            str(tijdGPS) + "," +
            str(lengtegraad_data) + "," +
            str(breedtegraad_data) + "," +
            str(hoogte_data) + "," +
            str(constants.sensor_id) + "\n"
        )

    if len(pressList) > 0:
        try:
            druk = int(median(pressList))
            sensor.set_ambient_pressure(druk)
            print("Minuut opgeslagen. Druk voor SCD4X:", druk)
        except Exception as e:
            print("Drukcompensatie SCD4X mislukt:", e)
    else:
        print("Minuut opgeslagen; geen geldige luchtdruk voor drukcompensatie.")


# ===== HOOFDPROGRAMMA =====
def main():
    init_scd()
    init_bme()
    init_dust()
    init_oled()

    co2List = []
    pressList = []
    tempList = []
    humList = []
    gasList = []
    PM25List = []
    PM10List = []
    hoogteList = []

    meetGPS()

    starttijd = time.ticks_ms()
    volgende_meting = starttijd
    laatste_opslag = starttijd
    volgende_opslag = time.ticks_add(starttijd, OPSLAGINTERVAL_MS)

    schermnummer = 0
    aantal_metingen = 0

    while True:
        nu = time.ticks_ms()

        if time.ticks_diff(nu, volgende_opslag) >= 0:
            if aantal_metingen > 0:
                schrijf_data(
                    co2List,
                    pressList,
                    tempList,
                    humList,
                    gasList,
                    PM25List,
                    PM10List,
                    hoogteList
                )

            co2List = []
            pressList = []
            tempList = []
            humList = []
            gasList = []
            PM25List = []
            PM10List = []
            hoogteList = []
            aantal_metingen = 0

            laatste_opslag = volgende_opslag
            volgende_opslag = time.ticks_add(
                volgende_opslag,
                OPSLAGINTERVAL_MS
            )

        if time.ticks_diff(nu, volgende_meting) >= 0:
            bme_ok = readBME()
            scd_ok = readSCD()
            dust_ok = readDust()

            nieuwe_gps_fix = meetGPS()

            if scd_ok:
                co2List.append(co2)

            if bme_ok:
                pressList.append(pres)
                tempList.append(temp)
                humList.append(hum)
                gasList.append(gas)

            if dust_ok:
                PM25List.append(PM25)
                PM10List.append(PM10)

            if nieuwe_gps_fix:
                try:
                    hoogteList.append(float(hoogte))
                except Exception:
                    pass

            aantal_metingen += 1

            toon_scherm(
                schermnummer,
                laatste_opslag,
                volgende_opslag
            )

            schermnummer = (schermnummer + 1) % 3

            volgende_meting = time.ticks_add(
                volgende_meting,
                MEETINTERVAL_MS
            )

        time.sleep_ms(20)


# ===== PROGRAMMA STARTEN =====
try:
    main()

except Exception as error:
    try:
        with open("error_log.txt", "a") as f:
            f.write("main.py fout: " + str(error) + "\n")
    except Exception:
        pass

    raise