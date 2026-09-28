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
# tijdGPS blijft bewust in UTC; lengtegraad, breedtegraad en hoogte bewaren de laatste fix.
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
                    # GPS-data kunnen ook binnenkomen zonder geldige positiebepaling.
                    # De GPS-tijd mag dan wel worden bijgewerkt en blijft in UTC.
                    tijdGPS = (
                        str(my_gps.date[2]) + ";" +
                        str(my_gps.date[1]) + ";" +
                        str(my_gps.date[0]) + ";" +
                        str(my_gps.timestamp[0]) + ";" +
                        str(my_gps.timestamp[1]) + ";" +
                        str(int(my_gps.timestamp[2]))
                    )

                    # Positie en hoogte alleen overschrijven bij een geldige GGA-fix.
                    # Zo gebruiken we coördinaten en hoogte uit dezelfde geldige GPS-zin.
                    try:
                        if stat in ("GPGGA", "GLGGA", "GNGGA") and my_gps.fix_stat > 0:
                            breedtegraad = my_gps.latitude_string()
                            lengtegraad = my_gps.longitude_string()
                            hoogte = my_gps.altitude
                            nieuwe_fix = True
                    except Exception:
                        # Als de fixstatus niet betrouwbaar kan worden gelezen,
                        # beschouwen we dit niet als een nieuwe geldige positie.
                        pass

    except Exception as e:
        print("GPS-fout:", e)

    return nieuwe_fix




# ===== BME680 UITLEZEN =====
# De BME680 levert temperatuur, relatieve vochtigheid, luchtdruk en gasweerstand.
# De gasweerstand wordt gedeeld door 1000 zodat gas in kOhm wordt bewaard en getoond.
def readBME():
    global temp, hum, pres, gas

    if bme is None and not init_bme():
        return False

    try:
        # ===== KALIBRATIEWAARDEN (y = a * x + b) =====
        # Pas onderstaande a- en b-waarden aan op basis van jouw kalibratieresultaten.
        a_temp = 1.0
        b_temp = 0.0
        a_hum = 1.0
        b_hum = 0.0
        a_pres = 1.0
        b_pres = 0.0

        # Pas de kalibratie toe op de ruwe sensormetingen.
        nieuwe_temp = (bme.temperature * a_temp) + b_temp
        nieuwe_hum = (bme.humidity * a_hum) + b_hum
        nieuwe_pres = (bme.pressure * a_pres) + b_pres
        
        nieuwe_gas = bme.gas / 1000

        # Pas de actuele waarden pas aan wanneer de volledige meting gelukt is.
        temp = nieuwe_temp
        hum = nieuwe_hum
        pres = nieuwe_pres
        gas = nieuwe_gas

        return True

    except Exception as e:
        print("BME680-fout:", e)
        return False


# ===== SCD4X UITLEZEN =====
# Van de SCD4X wordt alleen de CO2-meting gebruikt.
def readSCD():
    global co2

    if sensor is None and not init_scd():
        return False

    try:
        nieuwe_co2 = sensor.co2

        # Bewaar de nieuwe waarde alleen wanneer de uitlezing gelukt is.
        co2 = nieuwe_co2
        return True

    except Exception as e:
        print("SCD4X-fout:", e)
        return False


# ===== SDS011 UITLEZEN =====
# De SDS011 meet PM2.5 en PM10 in ug/m3.
# De meest recente waarden worden bewaard voor het OLED en voor de minuutmediaan.
def readDust():
    global PM25, PM10

    if dust_sensor is None and not init_dust():
        return False

    try:
        dust_sensor.read()
        nieuwe_PM25 = dust_sensor.pm25
        nieuwe_PM10 = dust_sensor.pm10

        # Bewaar beide waarden alleen wanneer de uitlezing gelukt is.
        PM25 = nieuwe_PM25
        PM10 = nieuwe_PM10

        return True

    except Exception as e:
        print("SDS011-fout:", e)
        return False


# ===== MEDIAAN =====
# De mediaan vermindert de invloed van korte pieken en toevallige uitschieters.
# Bij een even aantal waarden wordt het gemiddelde van de twee middelste waarden genomen.
def median(waarden):
    n = len(waarden)

    # Geen geldige metingen in deze minuut: schrijf 0 zodat dit herkenbaar blijft in DATA.
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
# Voor de lokale OLED-tijd moet ook de datum correct doorschuiven wanneer UTC+2
# over middernacht gaat. Deze hulpfuncties houden rekening met schrikkeljaren.
def is_schrikkeljaar(jaar):
    return jaar % 4 == 0 and (jaar % 100 != 0 or jaar % 400 == 0)


def dagen_in_maand(maand, jaar):
    dagen = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    if is_schrikkeljaar(jaar):
        dagen[1] = 29

    return dagen[maand - 1]


# ===== GPS-TIJD VOOR HET OLED =====
# tijdGPS zelf wordt niet gewijzigd en blijft dus UTC voor DATA.
# Alleen voor het OLED maken we hier een lokale kopie met UTC_OFFSET_UREN erbij.
def gps_tekst_lokaal():
    if tijdGPS == 0:
        return "Datum:--/--/----", "Tijd: --:--"

    try:
        delen = str(tijdGPS).split(";")

        if len(delen) < 5:
            return "Datum:--/--/----", "Tijd: --:--"

        jaar = int(delen[0]) + 2000
        maand = int(delen[1])
        dag = int(delen[2])
        uur = int(delen[3])
        minuut = int(delen[4])

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
# Per meetmoment wordt precies één scherm getoond. Het scherm blijft daarna staan
# tot de volgende meting, zodat het OLED de 10-secondenplanning niet blokkeert.
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
        # Een tijdelijk OLED-probleem mag de datalogging niet stoppen.
        print("OLED-fout:", e)


# ===== DATA WEGSCHRIJVEN =====
# Elke minuut wordt per sensor de mediaan van maximaal zes geldige 10-secondenmetingen opgeslagen.
# GPS-coördinaten worden alleen bewaard als er in die minuut minstens één geldige fix was.
# Zonder geldige fix gedurende de volledige minuut worden lengtegraad, breedtegraad en hoogte 0.
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
    # De eerste kolom blijft, zoals in de oorspronkelijke code, de looptijd in minuten.
    tijd = time.ticks_ms() / 1000 / 60

    # hoogteList bevat alleen hoogtes van geldige GPS-fixes uit de lopende minuut.
    # Bij minstens één fix bewaren we de laatste geldige positie en de mediaan van de hoogtes.
    # Bij een volledige minuut zonder fix schrijven we 0, zodat GPS-uitval herkenbaar blijft.
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

    # De mediaan van de luchtdruk wordt aan de SCD4X doorgegeven
    # zodat de CO2-meting drukgecompenseerd kan worden.
    # Een fout hierbij mag de verdere datalogging niet stoppen.
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
# De planning gebruikt vaste klokmomenten: 0, 10, 20, 30, 40 en 50 seconden.
# Daardoor wordt de duur van een sensormeting niet telkens boven op het interval geteld.
def main():
    # Probeer alle sensoren en het OLED-scherm afzonderlijk te starten.
    # Een onderdeel dat hier niet reageert, wordt later automatisch opnieuw geprobeerd.
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

    # Probeer onmiddellijk bij het opstarten GPS-data te lezen.
    # Als er nog geen fix is, wordt de GPS daarna automatisch elke 10 seconden opnieuw gelezen.
    meetGPS()

    starttijd = time.ticks_ms()
    volgende_meting = starttijd
    laatste_opslag = starttijd
    volgende_opslag = time.ticks_add(starttijd, OPSLAGINTERVAL_MS)

    schermnummer = 0
    aantal_metingen = 0

    while True:
        nu = time.ticks_ms()

        # Eerst de voorbije minuut opslaan wanneer de 60-secondenmarkering bereikt is.
        # Zo behoort de meting op exact 60 s al tot de volgende minuut.
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

            # Na de opslag starten alle lijsten opnieuw leeg voor de volgende minuut.
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

        # Een nieuwe meetronde start op vaste tijdstippen om de 10 seconden.
        # Sensoren die bij het opstarten ontbraken, worden hier automatisch opnieuw geprobeerd.
        if time.ticks_diff(nu, volgende_meting) >= 0:
            bme_ok = readBME()
            scd_ok = readSCD()
            dust_ok = readDust()

            # GPS wordt eveneens om de 10 seconden verwerkt.
            # Alleen een nieuwe geldige fix wordt gebruikt voor de hoogte-mediaan.
            nieuwe_gps_fix = meetGPS()

            # Alleen werkelijk geslaagde sensormetingen gaan naar de minuutlijsten.
            # Zo wordt bij een tijdelijke sensorfout geen oude waarde opnieuw opgeslagen.
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

            # Toon na iedere meting het volgende OLED-scherm.
            # Elk scherm blijft ongeveer 10 seconden zichtbaar tot de volgende meetronde.
            toon_scherm(
                schermnummer,
                laatste_opslag,
                volgende_opslag
            )

            schermnummer = (schermnummer + 1) % 3

            # Tel 10 seconden bij het geplande tijdstip op, niet bij het einde van de meting.
            # Daardoor blijft de planning zo dicht mogelijk bij 0,10,20,30,40,50 s.
            volgende_meting = time.ticks_add(
                volgende_meting,
                MEETINTERVAL_MS
            )

        # Een zeer korte slaap voorkomt dat de ESP32 nutteloos in een lege lus blijft draaien.
        time.sleep_ms(20)


# ===== PROGRAMMA STARTEN =====
# Eventuele onverwachte fouten worden in error_log.txt bewaard.
# Daarna wordt de fout opnieuw opgegooid zodat ze ook zichtbaar blijft in Thonny.
try:
    main()

except Exception as error:
    try:
        with open("error_log.txt", "a") as f:
            f.write("main.py fout: " + str(error) + "\n")
    except Exception:
        pass

    raise