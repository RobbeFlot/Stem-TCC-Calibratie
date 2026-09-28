# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

f = open('error_log.txt', 'a')
f.write("meetcel werd herstart\n")
f.close()
fdata=open('DATA',"a")
fdata.write("Tijd,CO2,TempBME,RHBME,Press,Rvoc,PM2.5,PM10,TijdGPS,LengteGr,BreedteGr,Hoogte,Sensornummer\n")
fdata.close()
