import pandas as pd
import matplotlib.pyplot as plt

def regressie(xValues : list, yValues : list) -> tuple[float, float]:
    #checking if the x and y list have the same amount of values!
    if(len(xValues) != len(yValues)):
        raise ValueError("xValues and yValues are do not have an equal size!")

    #getting the n (n = #elements)
    n = len(xValues)
    if(n == 0):
        raise ValueError("No values found for xValues!")

    #getting the values we need
    xy = list(map(lambda x, y: x * y, xValues, yValues))
    xSquared = list(map(lambda x: x*x, xValues))

    #calculating a and b
    try:
        a = (n * sum(xy) - sum(xValues) * sum(yValues)) / (n * sum(xSquared) - sum(xValues) * sum(xValues))
        b = (sum(yValues) - a * sum(xValues)) / n
        return a, b
    except ZeroDivisionError:
        print("All x values are equal! --> ZeroDevisionError")

def getData(WEATHERSTATIONFILE : str, BIRDFILE : str) -> dict[str, list]:
    #getting the files
    weatherStationData = pd.read_csv(f"csv/{WEATHERSTATIONFILE}.csv")
    birdsData = pd.read_csv(f"csv/{BIRDFILE}.csv")

    #Removing all the data we don't need (looking at the values on specific spots in the data and checking if they are useful)
    for i, row in birdsData.iterrows():
        try:
            str(birdsData["TijdGPS"][i])[15]
        except:
            birdsData.drop(i, inplace = True)
            continue
        if str(birdsData["TijdGPS"][i])[15] != "0":
            birdsData.drop(i, inplace = True)
            continue
        elif int(str(birdsData["TijdGPS"][i])[12]) < 6 and int(str(birdsData["TijdGPS"][i])[11]) < 2:
            birdsData.drop(i, inplace = True)
            continue
    birdsData = birdsData.reset_index(drop = True)

    #putting the data in dictionaries and returning the two dicts as one
    weatherStationDataDic = dict(weatherStationData)
    birdsDataDic = dict(birdsData)
    return weatherStationDataDic | birdsDataDic

def plot(xLabel : str, yLabel : str, title : str, xValues : list, data1 : list, data2 : list, size : int) -> None:
    plt.xlabel(xLabel)
    plt.ylabel(yLabel)
    plt.title(title)
    plt.scatter(xValues, data1, s=size)
    plt.scatter(xValues, data2, s=size)

    plt.show()

running = True
while(running):
    print("Menu:")
    print("\t--Plot (p)")
    print("\t--Quit (q)")
    ans = input("--")
    if ans == "p":
        print("Menu:")
        print("\t--Dinsdag (di)")
        print("\t--Woensdag (woe)")
        ans = input("--")
        if ans == "di":
            #Wich bird and wich value
            BIRDFILE = "5"
            SENSORB = "TempBME"
            SENSORW = "temperatuur_tl"
            data = getData("weerstation", f"{BIRDFILE}")
            
            #getting the y values (1-x, with x = the amount of data)
            xValues = []
            for i in range(len(data[SENSORB])):
                xValues.append(i)

            #plotting
            xLabel = "Measurement"
            yLabel = "Temperature (°C)"
            title = "Measured and accurate temperature"
            size = 10
            
            plot(xLabel, yLabel, title, xValues, data[SENSORW], data[SENSORB], size)
        elif ans == "woe":
            #Wich bird and wich value
            BIRDFILE = "5"
            SENSORB = "TempBME"
            SENSORW = "temperatuur_tl"
            data = getData("weerstation", f"{BIRDFILE}")

            HIKEDATA = pd.read_csv("csv/hikedata.csv")

            #getting the y values (1-x, with x = the amount of data)
            xValues = []
            for i in range(len(HIKEDATA["TempBME"])):
                xValues.append(i)

            #calculating regression values
            _regressie = regressie(data[SENSORB], data[SENSORW])
            newData = []
            for i in range(len(HIKEDATA["TempBME"])):
                newData.append(_regressie[0] * HIKEDATA["TempBME"][i] + _regressie[1])

            #plotting
            xLabel = "Measurement"
            yLabel = "Temperature (°C)"
            title = "Measured and calibrated temperature from the hike"
            size = 1

            plot(xLabel, yLabel, title, xValues, HIKEDATA["TempBME"], newData, size)
        else:
            print("INVALID MENU OPTION!")
    elif ans == "q":
        running = False
    else:
        print("INVALID MENU OPTION")
