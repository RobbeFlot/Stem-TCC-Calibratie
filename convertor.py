import pandas as pd
from datetime import timedelta

FILENAME = input("Enter file number: ")
PATH = f"data/{FILENAME}.txt"

df = pd.read_csv(f"{PATH}")
df = df[df["Tijd"] != "Tijd"]
df = df.reset_index(drop = True)

df["TijdGPS"] = pd.to_datetime(
    df["TijdGPS"],
    format="%y;%m;%d;%H;%M;%S",
    errors="coerce"
)

df["TijdGPS"] = (
    df["TijdGPS"]
    .dt.tz_localize("UTC")
    .dt.tz_convert("Europe/Brussels")
)

df = df[["TempBME", "RHBME", "Press", "TijdGPS"]]

df.to_csv(f"csv/{FILENAME}.csv")