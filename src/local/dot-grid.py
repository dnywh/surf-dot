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

    # Get swell height
    swellData = surfData["forecasts"]["swell"]["days"][0]["entries"]
    swellDataHeights = []

    # print(len(swellData))
    for val in swellData:
        convertedHeight = int(numberToRange(
            val["height"], 0, 3, 1, cellScale * 1.5))
        # print(val["height"], "->",
        #       convertedHeight)
        swellDataHeights.append(convertedHeight)
    # print(swellDataHeights)
    # print()
    # print(swellData)

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
            circleWidth = swellDataHeights[jj]
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
