# Stem-TCC-Calibratie

api.py:
    Haalt de nodige gegevens (om de 10 minuten) van de weerstations en zet deze in een .csv file

converter.py:
    Zet de gegevens van de vogeltjes (.txt) om naar een .csv

main.py:
    Regressie:
        Berekent de regressielijn van de data.
    
    calculateCalibrationValues:
        Gebruikt de functie (y = ax + b) van de regressielijn van zowel de data van de weerstations als de data van de vogeltjes om een afwijking te berekenen (ook een functie van de vorm y = ax + b). De a & b waarde van deze functie hebben we nodig om de vogeltjes te calibreren.