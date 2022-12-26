import env
import requests
from datetime import datetime
from PIL import Image, ImageDraw

# import numpy as np
from scipy import signal

# Secrets
# Renamed to 'env' to avoid clashing with numpy
ssid = env.SSID
password = env.PASSWORD
willyWeatherApiKey = env.WILLY_WEATHER_API_KEY

# Customise for your location
locationId = 6833  # Coolum Beach
locationMaxSwellHeight = 3
locationMaxTideHeight = 3  # TODO: Must this match the SwellHeight?
locationWindDirRangeStart = 180
locationWindDirRangeEnd = 315
# Amount of degrees on either side of range to consider as 'okay' wind conditions
locationWindDirRangeBuffer = 22

# Customise hours 'cropped' from left to right
hourStart = 6
hourEnd = 18

# Set cols and rows (grid size)
cols = 24
rows = 24
# Set scale for each cell
cellScale = 16

# Set design basics
maxDotSizeActive = 20
minDotSizeActive = 4
minDotSizeInactive = 2

# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

# Number to range function for general mapping
def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


# A function that takes a list of length 24, containing tuples
# Trims that list to the hourStart and hourEnd window
# Then resamples (upscales) that list to match the amount of columns (which by default is also 24)
def resampleList(originalList, targetTupleItem):
    simplifiedList = []
    trimmedList = []
    for i in originalList:
        k = i[targetTupleItem]
        simplifiedList.append(k)
    # Assumes the input list is 24 (hours) long
    trimmedList = simplifiedList[hourStart:hourEnd]
    resampledList = signal.resample(trimmedList, cols)
    return resampledList


try:
    date = datetime.today().strftime("%Y-%m-%d")
    date = "2022-12-29"  # Override with a custom date (Willy Weather's API is limited to +-2 days from today)
    print(f"Checking surf for {date}...")

    # Parse surf data
    surfData = requests.get(
        f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}"
    ).json()

    tideData = surfData["forecasts"]["tides"]["days"][0]["entries"]
    tidesKnown = []
    tidesAll = [(0, "unknown")] * cols
    tidesMapped = []

    swellData = surfData["forecasts"]["swell"]["days"][0]["entries"]
    swellDataScores = []

    windData = surfData["forecasts"]["wind"]["days"][0]["entries"]
    windDataScores = []

    # Tides
    # Replace known items
    for i in tideData:
        # Calculate index of each tide data element based on time
        dateString = datetime.strptime(i["dateTime"], "%Y-%m-%d %H:%M:%S")
        hour = int(datetime.strftime(dateString, "%H"))
        min = int(datetime.strftime(dateString, "%M"))
        minAsFraction = min / 60
        timeAsIndexThroughDay = round(hour + minAsFraction)
        tidesAll[timeAsIndexThroughDay] = (i["height"], i["type"])
        tidesKnown.append((timeAsIndexThroughDay, i["height"], i["type"]))

    # Calculate unknown tides in between known ones
    for i in range(len(tidesKnown) - 1):
        selectedTide = tidesKnown[i]  # The current tuple in the list
        nextTide = tidesKnown[i + 1]  # The next tuple in the list
        # Get the height difference in these two tuples
        difference = nextTide[1] - selectedTide[1]
        # Get the index difference in these two tuples
        step = nextTide[0] - selectedTide[0]
        # Figure out how much height each index in-between must increment/decrement
        increment = difference / step
        # Note the direction of the step
        direction = "increasing" if increment > 0 else "decreasing"
        # Save this increment and direction to the larger tides list
        for k in range(selectedTide[0] + 1, nextTide[0]):
            calculatedStep = (tidesAll[k - 1][0] + increment, direction)
            tidesAll[k] = calculatedStep

    # Resample items to match hourStart and hourEnd window
    tidesResampled = resampleList(tidesAll, 0)

    # Lastly map each item value to match the amount of rows for a nice Y pos
    for i in tidesResampled:
        mappedY = round(numberToRange(i, 0, locationMaxTideHeight, 2, rows))
        # Add this value to the new array
        tidesMapped.append(mappedY)
    print("Tides:\t", tidesMapped)

    # Swell height
    # Resample items to match hourStart and hourEnd window
    swellDataResampled = resampleList(swellData, "height")
    # Create scores
    for i in swellDataResampled:
        mappedHeight = int(numberToRange(i, 0, locationMaxSwellHeight, 0, 12))
        swellDataScores.append(mappedHeight)
    print("Swell:\t", swellDataScores)

    # Wind direction and speed
    # Resample items to match hourStart and hourEnd window
    windSpeedDataResampled = resampleList(windData, "speed")
    windDirDataResampled = resampleList(windData, "direction")
    for i in range(cols):
        mappedSpeed = int(numberToRange(windSpeedDataResampled[i], 0, 30, 0, 6))
        # Core range
        if (
            windDirDataResampled[i] >= locationWindDirRangeStart
            and windDirDataResampled[i] <= locationWindDirRangeEnd
        ):
            # Best possible wind conditions, give high score
            windDataScores.append(8 + mappedSpeed)
        # -locationWindDirRangeBuffer° of core range start
        elif (
            windDirDataResampled[i]
            >= locationWindDirRangeStart - locationWindDirRangeBuffer
            and windDirDataResampled[i] < locationWindDirRangeStart
        ):
            # Okay wind conditions, give medium score
            windDataScores.append(4 + mappedSpeed)
        # +locationWindDirRangeBuffer° of core range end
        elif (
            windDirDataResampled[i] > locationWindDirRangeEnd
            and windDirDataResampled[i]
            <= locationWindDirRangeEnd - locationWindDirRangeBuffer
        ):
            # Okay wind conditions, give medium score
            windDataScores.append(4 + mappedSpeed)
        else:
            # Poor wind conditions, give nothing
            # Subtract increased wind since it's blowing in the wrong direction
            windDataScores.append(0 - mappedSpeed)
    print("Wind:\t", windDataScores)

    # Combine all of the above into a final score
    combinedScores = []
    for i in range(rows):
        # Add the values together
        sum = swellDataScores[i] + windDataScores[i]
        if sum < minDotSizeActive:
            # This dot has a poor score, probably dragged down by poor wind
            # Assign it the minimum active dot size
            combinedScores.append(minDotSizeActive)
        else:
            # This dot has a solid score and can render at its score
            combinedScores.append(sum)
    print("Scores:\t", combinedScores)

    # Start rendering
    canvas = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 255)  # 255: clear the frame
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

            # Without tides
            # dotSize = combinedScores[jj]

            # With tides
            # Use negative value to anchor at last row
            if rows - (tidesMapped[jj]) <= kk:
                # This dot's coordinates are within the tide height, so render fully according to its score
                dotSize = combinedScores[jj]
                # dotSize = int(
                #     numberToRange(
                #         combinedScores[jj], -10, 30, minDotSizeActive, maxDotSizeActive
                #     )
                # )
                # print(dotSize)
            else:
                # This dot's coordinates are outside the tide height so render as small as possible irrespective of its score
                dotSize = minDotSizeInactive

            # Calculate how to center this dot
            itemOffset = int((cellScale - dotSize) / 2)

            # Draw the dot
            draw.ellipse(
                (
                    (cellX + itemOffset, cellY + itemOffset),
                    (cellX + itemOffset + dotSize, cellY + itemOffset + dotSize),
                ),
                fill="black",
            )

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
