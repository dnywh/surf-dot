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

# Set cols and rows (grid size)
cols = 24
rows = 24
# Set scale for each cell
cellScale = 16

# Set design basics
minDotSizeActive = 8
minDotSizeInactive = 2

# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

# Number to range function for general mapping
# https://www.30secondsofcode.org/python/s/num-to-range


def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


try:
    print("Checking surf...")

    date = datetime.today().strftime('%Y-%m-%d')

    # Parse surf data
    surfData = requests.get(
        f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}").json()

    tideData = surfData["forecasts"]["tides"]["days"][0]["entries"]
    # tidesList = [None] * cols
    tidesList = [0] * cols  # Set to a default value for testing
    tidesListMapped = []
    tidesKnownIndexes = []

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
        tidesKnownIndexes.append(timeAsIndexThroughDay)
        tidesList[timeAsIndexThroughDay] = i["height"]
    print(tidesKnownIndexes)
    print(tidesList)

    # Fill in missing items
    # for i in tidesList:
    #     if i != None:
    # steps = []
    # for item, index in tidesKnownIndexes:
    #     if index > 0:
    #         steps.append(index + 1 - index)
    # print(steps)

    # for i in range(cols):
    #     # If there already exists a known tide at this index...
    #     if tidesKnown[i][1]:
    #         # Append it to the full list
    #         tidesList.append(tidesKnown[i][1])
    #     else:
    #         # Calculate this index's value
    #         tidesList.append(0.00)

    # Lastly map each item value to match the amount of rows for a nice Y pos
    for i in tidesList:
        mappedY = round(numberToRange(i, 0, locationMaxTideHeight, 2, rows))
        # Add this value to the new array
        tidesListMapped.append(mappedY)
    print(tidesListMapped)

    # Swell height
    # 24 items by default (item amount should equal rows amount)
    for i in swellData:
        mappedHeight = int(numberToRange(
            i["height"], 0, locationMaxSwellHeight, 0, 14))
        swellDataScores.append(mappedHeight)
    # print(swellDataScores)

    # Wind direction and speed
    # 24 items by default (item amount should equal rows amount)
    for i in windData:
        mappedSpeed = int(numberToRange(i["speed"], 0, 30, 0, 10))
        # TODO: make range/map rather than if statement
        # Core range
        if i["direction"] >= locationWindDirRangeStart and i["direction"] <= locationWindDirRangeEnd:
            # Best possible wind conditions, give high score
            windDataScores.append(10 + mappedSpeed)
        # -45° of core range start
        elif i["direction"] >= locationWindDirRangeStart - 45 and i["direction"] < locationWindDirRangeStart:
            # Okay wind conditions, give medium score
            windDataScores.append(6 + mappedSpeed)
         # +45° of core range end
        elif i["direction"] > locationWindDirRangeEnd and i["direction"] <= locationWindDirRangeEnd - 45:
            # Okay wind conditions, give medium score
            windDataScores.append(6 + mappedSpeed)
        else:
            # Poor wind conditions, give nothing
            # Subtract increased wind since it's blowing in the wrong direction
            windDataScores.append(0 - mappedSpeed)
    # print(windDataScores)

    # Combine all of the above into a final score
    combinedScores = []
    for i in range(rows):
        # Add the values together
        sum = swellDataScores[i] + windDataScores[i]
        if sum < 1:
            # For a negative score sum, set to a minimum so a visible dot appears
            combinedScores.append(minDotSizeActive)
        else:
            # Otherwise show the true score sum
            combinedScores.append(sum)
    # print(combinedScores)

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
            # dotWidth = random.randint(2, cellScale * 1.5)
            # dotWidth = 2

            # Without tides
            dotWidth = combinedScores[jj]

            # With tides
            # Reversed to anchor at bottom
            if rows - (tidesListMapped[jj]) <= kk:
                # This dot's coordinates are within the tide height, so render fully according to its score
                dotWidth = combinedScores[jj]
            else:
                # This dot's coordinates are outside the tide height so render as small as possible irrespective of its score
                dotWidth = minDotSizeInactive

            # Calculate how to center this dot
            itemOffset = int((cellScale - dotWidth) / 2)

            # Draw the dot
            draw.ellipse(
                ((cellX + itemOffset, cellY + itemOffset), (cellX + itemOffset + dotWidth, cellY + itemOffset + dotWidth)), fill="black")

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
