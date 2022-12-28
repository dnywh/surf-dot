import env
import requests
from datetime import datetime
from PIL import Image, ImageDraw

from scipy import signal  # for figuring out tide heights between hours
import json


# Secrets
# Renamed to 'env' to avoid clashing with numpy's required file of the same name
willyWeatherApiKey = env.WILLY_WEATHER_API_KEY

# Customise for your location
locationId = 6833  # Coolum Beach
locationMaxSwellHeight = 3
locationMaxTideHeight = 3  # TODO: Must this match the SwellHeight?
locationWindDirRangeStart = 225
locationWindDirRangeEnd = 315
# Amount of degrees on either side of range to consider as 'okay' wind conditions
locationWindDirRangeBuffer = 45

debug = False

# Customise hours 'cropped' from left to right
hourStart = 6
hourEnd = 18

# Set design basics
containerWidth = 384
# Set cols and rows (grid size)
cols = 24  # Must be at least 24
rows = cols
# Set scale for each cell
cellSize = containerWidth / cols
maxDotSizeActive = cellSize * 2
minDotSizeActive = 4
minDotSizeInactive = 2

# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

# Number to range function for general mapping
def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


# A function that takes a list of length 24, containing tuples,
# ...trims that list to the hourStart and hourEnd window,
# ...then resamples (upscales) that list to match the amount of columns (which by default is also 24)
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
    # Load data
    if debug == True:
        date = "Example "
        print(f"Debugging is on.\nChecking surf from example data file...")
        f = open("src/example.json")
        surfData = json.load(f)
    else:
        # date = "2022-12-29"  # Optional override with a custom date (Willy Weather's API is limited to +-2 days from today)
        date = datetime.today().strftime("%Y-%m-%d")
        print(f"Checking surf for {date}...")
        surfData = requests.get(
            f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}"
        ).json()

    # Parse data
    tideData = surfData["forecasts"]["tides"]["days"][0]["entries"]
    tidesAll = [(0, "unknown")] * cols  # Blank list to fill in later

    swellData = surfData["forecasts"]["swell"]["days"][0]["entries"]
    windData = surfData["forecasts"]["wind"]["days"][0]["entries"]

    # Swell height
    # Resample items to match hourStart and hourEnd window
    swellDataResampled = resampleList(swellData, "height")
    # Create scores
    swellScores = []
    for i in swellDataResampled:
        mappedHeight = int(
            numberToRange(i, 0, locationMaxSwellHeight, 0, maxDotSizeActive * 0.7)
        )
        swellScores.append(mappedHeight)
    print("————————————", "\nSwell Score:\t", swellScores)

    # Wind direction and speed
    # Resample items to match hourStart and hourEnd window
    windSpeedDataResampled = resampleList(windData, "speed")
    windDirDataResampled = resampleList(windData, "direction")
    windScores = []
    for i in range(cols):
        mappedSpeed = int(
            numberToRange(windSpeedDataResampled[i], 0, 30, 0, maxDotSizeActive * 0.3)
        )
        # Core range
        if (
            windDirDataResampled[i] >= locationWindDirRangeStart
            and windDirDataResampled[i] <= locationWindDirRangeEnd
        ):
            # Best possible wind conditions, give high score
            windScores.append(int(maxDotSizeActive * 0.4 + mappedSpeed))
        # Core range - buffer
        elif (
            windDirDataResampled[i]
            >= locationWindDirRangeStart - locationWindDirRangeBuffer
            and windDirDataResampled[i] < locationWindDirRangeStart
        ):
            # Okay wind conditions, give medium score
            windScores.append(int(maxDotSizeActive * 0.2 + mappedSpeed))
        # Core range + buffer
        elif (
            windDirDataResampled[i] > locationWindDirRangeEnd
            and windDirDataResampled[i]
            <= locationWindDirRangeEnd - locationWindDirRangeBuffer
        ):
            # Okay wind conditions, give medium score
            windScores.append(int(maxDotSizeActive * 0.2 + mappedSpeed))
        else:
            # Poor wind conditions, give nothing
            # Subtract increased wind since it's blowing in the wrong direction
            windScores.append(int(0 - mappedSpeed))
    print("Wind Score:\t", windScores)

    # Combine all of the above into a total score
    totalScores = []
    for i in range(rows):
        # Add the values together
        sum = swellScores[i] + windScores[i]
        if sum < minDotSizeActive:
            # This dot has a poor score, probably dragged down by poor wind
            # Assign it the minimum active dot size
            totalScores.append(minDotSizeActive)
        else:
            # This dot has a solid score and can render at its score
            totalScores.append(sum)
    print("Total Score:\t", totalScores)

    # Tides
    # Replace known items
    tidesKnown = []
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
    tidesMapped = []
    for i in tidesResampled:
        mappedY = round(numberToRange(i, 0, locationMaxTideHeight, 2, rows))
        # Add this value to the new array
        tidesMapped.append(mappedY)
    print("————————————", "\nTides Height:\t", tidesMapped, "\n————————————")

    # Start rendering
    canvas = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 255)  # 255: clear the frame
    # Get a drawing context
    draw = ImageDraw.Draw(canvas)

    # Center grid
    offsetX = int((EPD_WIDTH - (cols * cellSize)) / 2)
    offsetY = int((EPD_HEIGHT - (rows * cellSize)) / 2)

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

            # Without tides: unlimited data across full columns
            # dotSize = totalScores[jj]
            # dotSize = totalScores[jj] - (dropOff * kk)

            # With tides: limited data to within tide height range
            # Use negative value to anchor at last row
            if rows - (tidesMapped[jj]) <= kk:
                # This dot's coordinates are within the tide height, so render fully according to its score
                # Consistent dot sizing down column:
                # dotSize = totalScores[jj]

                # Decayed dot sizing down column:
                startRow = rows - tidesMapped[jj]
                currentRow = kk
                lastRow = rows - 1

                maxDotSizeValue = totalScores[jj]

                mappedDecay = int(
                    numberToRange(
                        currentRow, startRow, lastRow, maxDotSizeValue, minDotSizeActive
                    )
                )
                dotSize = mappedDecay

            else:
                # This dot's coordinates are outside the tide height so render as small as possible irrespective of its score
                dotSize = minDotSizeInactive

            # Calculate the center of this dot according to its size
            itemOffset = int((cellSize - dotSize) / 2)

            draw.ellipse(
                (
                    (cellX + itemOffset, cellY + itemOffset),
                    (cellX + itemOffset + dotSize, cellY + itemOffset + dotSize),
                ),
                fill="black",
            )

            # Move to the next column in the row
            valueX += cellSize
            # Store what gridIndex we're up to
            gridIndex += 1
        # Go to next row down
        valueY += cellSize
        # Go to first column on left
        valueX = 0

    canvas.show()

# Exit plan
except KeyboardInterrupt:
    print("Exiting...")
    exit()
