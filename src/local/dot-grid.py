from PIL import Image, ImageDraw
import random
# import math
import secrets
from time import sleep


import requests
# import urequests

from datetime import datetime
# import utime


# Secrets
# ssid = secrets.SSID
# password = secrets.PASSWORD
willyWeatherApiKey = secrets.WILLY_WEATHER_API_KEY

# Customise for location
locationId = 6833  # Coolum Beach
locationMaxSwellHeight = 3

# Set cols and rows (grid size)
cols = 24
rows = 24
# Set scale for each cell
cellScale = 16


# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

# Number to range function for general mapping
# https://www.30secondsofcode.org/python/s/num-to-range


def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


def connect():
    # Connect to WLAN
    print("Connecting...")


# def checkSurf():


try:
    print("Trying...")
    connect()

    print("Checking surf...")
    date = datetime.today().strftime('%Y-%m-%d')
    # datetime = f"{utime.localtime()[0]}-{utime.localtime()[1]}-{utime.localtime()[2]}"
    surfData = requests.get(
        f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}").json()

    swellData = surfData["forecasts"]["swell"]["days"][0]["entries"]
    swellDataHeights = []

    windData = surfData["forecasts"]["wind"]["days"][0]["entries"]
    windDataDirections = []
    windDataSpeeds = []

    # Swell height
    # 24 items by default (should equal rows length)
    for val in swellData:
        mappedHeight = int(numberToRange(
            val["height"], 0, 3, 0, 16))
        swellDataHeights.append(mappedHeight)
    # print(swellDataHeights)

    # Wind direction
    # 24 items by default (should equal rows length)
    for val in windData:
        # TODO: make range/map rather than if statement
        if val["direction"] >= 180 and val["direction"] <= 315:
            # Best possible wind conditions, give high score
            windDataDirections.append(10)
        elif val["direction"] >= 135 and val["direction"] < 180:
            # Okay wind conditions, give medium score
            windDataDirections.append(6)
        else:
            # Poor wind conditions, give nothing
            windDataDirections.append(0)
    # print(windDataDirections)

     # Wind speed
    # 24 items by default (should equal rows length)
    # TODO: Merge in wind direction because strong speed in the *wrong* direction is extra bad
    for val in windData:
        mappedSpeed = int(numberToRange(
            val["speed"], 0, 30, 0, 10))
        windDataSpeeds.append(mappedSpeed)
    print(windDataSpeeds)

    # Combine all of the above into a final score
    combinedScores = []
    for i in range(0, rows):
        # Add the values together
        combinedScores.append(
            swellDataHeights[i] + windDataDirections[i] + windDataSpeeds[i])


# Start rendering
    canvas = Image.new(
        "1", (EPD_WIDTH, EPD_HEIGHT), 255
    )  # 255: clear the frame
    # Get a drawing context
    draw = ImageDraw.Draw(canvas)

    # Center grid
    offsetX = int((EPD_WIDTH - (cols * cellScale)) / 2)
    offsetY = int((EPD_HEIGHT - (rows * cellScale)) / 2)

    # Prepare variables
    gridIndex = 0
    valueX = 0
    valueY = 0

    # Traverse through rows top to bottom
    for kk in range(rows):
        # Traverse through cols left to right
        for jj in range(cols):
            cellX = valueX + offsetX
            cellY = valueY + offsetY

            # Container
            # draw.rectangle(
            #     ((cellX, cellY), (cellX + cellScale, cellY + cellScale)), fill="white")

            # Shape
            # Paint another square within that square at that grid coordinate
            # circleWidth = random.randint(2, cellScale * 1.5)
            # circleWidth = 2
            circleWidth = combinedScores[jj]
            itemOffset = int((cellScale - circleWidth) / 2)
            draw.ellipse(
                ((cellX + itemOffset, cellY + itemOffset), (cellX + itemOffset + circleWidth, cellY + itemOffset + circleWidth)), fill="black")

            # Move to the next column in the row
            valueX += cellScale
            # Store what gridIndex we're up to
            gridIndex += 1
        # Go to next row down
        valueY += cellScale
        # Go to first column on left
        valueX = 0

    canvas.show()

# Exit plan
except KeyboardInterrupt:
    print("Exiting...")
    exit()
