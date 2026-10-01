import requests
import pandas as pd

station_ids = "11127"
parameters = "TL,RF,P"
start = "2026-09-29T16:00"
end = "2026-09-29T21:30"

url = f"https://dataset.api.hub.geosphere.at/v1/station/historical/tawes-v1-10min?station_ids={station_ids}&parameters={parameters}&start={start}&end={end}"
response = requests.get(url)

data = response.json()
timestamps = data["timestamps"]
station_data = data["features"][0]["properties"]["parameters"]

tabel_data = {
    "tijdstip": timestamps,
    "temperatuur_tl": station_data["TL"]["data"],
    "luchtvochtigheid_rf": station_data["RF"]["data"],
    "luchtdruk_p": station_data["P"]["data"]
}

df = pd.DataFrame(tabel_data)
df.to_csv("csv/weerstation.csv", index=False, sep=";")

print("File saved")