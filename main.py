#import numpy as np
#import matplotlib.pyplot as plt
#import pandas as pd

def regressie(xValues : list, yValues : list) -> tuple[int, int]:
    #checking if the x and y list have the same amount of values!
    if(len(xValues) != len(yValues)):
        print("Reference data & bird data have different sizes!")
        return

    #getting the n
    n = len(xValues)

    #getting the values we need
    xy = list(map(lambda x, y: x * y, xValues, yValues))
    xSquared = list(map(lambda x: x*x, xValues))

    #calculating a and b
    a = (n * sum(xy) - sum(xValues) * sum(yValues)) / (n * sum(xSquared) - sum(xValues) * sum(xValues))
    b = (sum(yValues) - a * sum(xValues)) / n
    return a, b

print(regressie([1, 1], [1, 1]))