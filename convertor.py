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

#eerste_geldige_rij = df["TijdGPS"].first_valid_index()

#if eerste_geldige_rij is not None:
#    referentietijd = df.loc[eerste_geldige_rij, "TijdGPS"]
#    referentie_tijd = df.loc[eerste_geldige_rij, "Tijd"]
#
#    for rij in df.index[df["TijdGPS"].isna()]:
#        verschil_minuten = float(df.loc[rij, "Tijd"]) - float(referentie_tijd)
#        df.loc[rij, "TijdGPS"] = (referentietijd + timedelta(minutes=verschil_minuten)).round("s")

df["TijdGPS"] = (
    df["TijdGPS"]
    .dt.tz_localize("UTC")
    .dt.tz_convert("Europe/Brussels")
)

df = df[["TempBME", "RHBME", "Press", "TijdGPS"]]

df.to_csv(f"csv/{FILENAME}.csv")