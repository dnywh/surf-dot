import secrets
import requests
from datetime import datetime
from PIL import Image, ImageDraw


# Secrets
ssid = secrets.SSID
password = secrets.PASSWORD
willyWeatherApiKey = secrets.WILLY_WEATHER_API_KEY

# Customise for your location
locationId = 6833  # Coolum Beach
locationMaxSwellHeight = 3
locationMaxTideHeight = 3  # TODO: Must this match the SwellHeight?
locationWindDirRangeStart = 180
locationWindDirRangeEnd = 315
# Amount of degrees on either side of range to consider as 'okay' wind conditions
locationWindDirRangeBuffer = 22

# Set cols and rows (grid size)
cols = 24
rows = 24
# Set scale for each cell
cellScale = 16

# Set design basics
minDotSizeActive = 4
minDotSizeInactive = 2

# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

# Number to range function for general mapping
# https://www.30secondsofcode.org/python/s/num-to-range


def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


try:
    date = datetime.today().strftime('%Y-%m-%d')
    print(f"Checking surf for {date}...")

    # Parse surf data
    surfData = requests.get(
        f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}").json()

    tideData = surfData["forecasts"]["tides"]["days"][0]["entries"]
    tidesAll = [(0, 'unknown')] * cols
    tidesKnown = []
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

    # Calculate tides at all other (~20) hours in the 24 hour list
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
        print(tidesAll)

    # Lastly map each item value to match the amount of rows for a nice Y pos
    for i in tidesAll:
        mappedY = round(numberToRange(i[0], 0, locationMaxTideHeight, 2, rows))
        # Add this value to the new array
        tidesMapped.append(mappedY)
    # print(tidesMapped)

    # Swell height
    # 24 items by default (item amount should equal rows amount)
    for i in swellData:
        mappedHeight = int(numberToRange(
            i["height"], 0, locationMaxSwellHeight, 0, 14))
        swellDataScores.append(mappedHeight)
    print("Swell:\t", swellDataScores)

    # Wind direction and speed
    # 24 items by default (item amount should equal rows amount)
    for i in windData:
        mappedSpeed = int(numberToRange(i["speed"], 0, 30, 0, 10))
        # TODO: make range/map rather than if statement
        # Core range
        if i["direction"] >= locationWindDirRangeStart and i["direction"] <= locationWindDirRangeEnd:
            # Best possible wind conditions, give high score
            windDataScores.append(10 + mappedSpeed)
            print("Great wind conditions at", i["dateTime"])
        # -locationWindDirRangeBuffer° of core range start
        elif i["direction"] >= locationWindDirRangeStart - locationWindDirRangeBuffer and i["direction"] < locationWindDirRangeStart:
            # Okay wind conditions, give medium score
            windDataScores.append(6 + mappedSpeed)
            print("Okay wind conditions at", i["dateTime"])
         # +locationWindDirRangeBuffer° of core range end
        elif i["direction"] > locationWindDirRangeEnd and i["direction"] <= locationWindDirRangeEnd - locationWindDirRangeBuffer:
            # Okay wind conditions, give medium score
            windDataScores.append(6 + mappedSpeed)
            print("Okay wind conditions at", i["dateTime"])
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
        if sum < 1:
            # This dot has a negative store, probably dragged down by poor wind
            # Check if its swellDataScore is larger than the dot size minimum
            if swellDataScores[i] > minDotSizeActive:
                # If so, set the dot size to its swellDataScore
                combinedScores.append(swellDataScores[i])
            else:
                # Otherwise the swellDataScore is still below the visible minimum, so set it to that
                combinedScores.append(minDotSizeActive)
        else:
            # This dot has a positive score and can render as intended
            combinedScores.append(sum)
    print("Scores:\t", combinedScores)

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

            # Without tides
            dotSize = combinedScores[jj]

            # With tides
            # Use negative value to anchor at last row
            if rows - (tidesMapped[jj]) <= kk:
                # This dot's coordinates are within the tide height, so render fully according to its score
                dotSize = combinedScores[jj]
            else:
                # This dot's coordinates are outside the tide height so render as small as possible irrespective of its score
                dotSize = minDotSizeInactive

            # Calculate how to center this dot
            itemOffset = int((cellScale - dotSize) / 2)

            # Draw the dot
            draw.ellipse(
                ((cellX + itemOffset, cellY + itemOffset), (cellX + itemOffset + dotSize, cellY + itemOffset + dotSize)), fill="black")

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
