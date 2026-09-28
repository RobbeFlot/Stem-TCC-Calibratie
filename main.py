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

def calculateCalibrationValues(reference : tuple[float, float], birdValues : tuple[float, float]) -> tuple[float, float]:
    return (birdValues[0] / reference[0], birdValues[1] / reference[1])    # (a, b)