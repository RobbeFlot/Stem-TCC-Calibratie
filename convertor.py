import pandas as pd

FILENAME = "testVals"

df = pd.read_csv("testVals.txt")
df = df[df["Tijd"] != "Tijd"]
df = df.reset_index(drop = True)
df = df[["TempBME", "RHBME", "Press", "TijdGPS"]]

df.to_csv(f"csv/{FILENAME}.csv")