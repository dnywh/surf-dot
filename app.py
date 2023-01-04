import sys
import os
import logging  # Write to console
from datetime import datetime
import requests
from scipy import signal  # For figuring out tide heights between hours
from PIL import Image, ImageDraw
import math  # For optional wind tail trigonometry
import json  # For debugging with local data

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Prepare directories so they can be reached from anywhere
appDir = os.path.dirname(os.path.realpath(__file__))
assetsDir = os.path.join(appDir, "assets")
# Get required items from other root-level directories
parentDir = os.path.dirname(appDir)
libDir = os.path.join(parentDir, "lib")
if os.path.exists(libDir):
    sys.path.append(libDir)

# Change the below import to match your display's driver
from waveshare_epd import epd5in83_V2 as display

# Adjust your optical offsets from one place
# import layout
# See Pi Frame for usage:
# https://github.com/dnywh/pi-frame

import env  # For Willy Weather access token

# Settings
willyWeatherApiKey = env.WILLY_WEATHER_API_KEY
headers = {"User-Agent": "Surf Grid", "From": "endless.paces-03@icloud.com"}
# Customise for your location
locationId = 6833  # Coolum Beach
locationMaxTideHeight = 3
locationMaxSwellHeight = 3
locationWindDirRangeStart = 225
locationWindDirRangeEnd = 315
# Amount of degrees on either side of range to consider as 'okay' wind conditions
locationWindDirRangeBuffer = 45

# Customise hours 'cropped' from left to right
hourStart = 6
hourEnd = 18

# Settings
margin = 36

# Shared optical sizing and offsets with Pi Frame
# containerSize = layout.size - margin
# offsetX = layout.offsetX
# offsetY = layout.offsetY
# Manual optical sizing and offsets
containerSize = 360 - margin
offsetX = 0
offsetY = 16

# Set cols and rows (grid size)
cols = 24  # Expects at least 24
rows = cols
# Set scale for each cell
cellSize = containerSize / cols
maxDotSizeActive = cellSize * 2
minDotSizeActive = 4
minDotSizeInactive = 2

showWindTail = False
debug = False  # Uses local data instead of API call if True

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
    timeStampNice = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Kicking off at {timeStampNice}")
    logging.info(
        f"Limiting surf data to between the hours of {hourStart:02d}:00 and {hourEnd:02d}:00"
    )

    # Load data
    if debug == True:
        logging.info(f"Debugging is on. Checking surf from example data file...")
        f = open(os.path.join(assetsDir, "2022-12-25.json"))
        surfData = json.load(f)
    else:
        date = datetime.today().strftime("%Y-%m-%d")
        # date = "2022-12-29"  # Optional override with a custom date (Willy Weather's API is limited to +-2 days from today)
        logging.info(f"Checking surf for {date}...")
        surfData = requests.get(
            f"https://api.willyweather.com.au/v2/{willyWeatherApiKey}/locations/{locationId}/weather.json?forecasts=tides,swell,wind&days=1&startDate={date}",
            headers=headers,
        ).json()

    # Parse data
    tideData = surfData["forecasts"]["tides"]["days"][0]["entries"]
    tidesAll = [
        (0, "unknown")
    ] * 24  # Blank list to fill in later, for all 24 hours of the day

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
    logging.info(f"Swell Score:\t{swellScores}")

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
    logging.info(f"Wind Score:\t{windScores}")

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
    logging.info(f"Total Score:\t{totalScores}")

    # Tides
    # Replace known items
    tidesKnown = []
    for i in tideData:
        # Calculate index of each tide data element based on time
        dateString = datetime.strptime(i["dateTime"], "%Y-%m-%d %H:%M:%S")
        hour = int(datetime.strftime(dateString, "%H"))
        min = int(datetime.strftime(dateString, "%M"))
        minAsFraction = min / 60
        # Round timestamp to nearest hour
        timeAsIndexThroughDay = round(hour + minAsFraction)
        # If nearest hour is within the 0–23 range
        if timeAsIndexThroughDay < 24:
            # Continue as planned
            tidesAll[timeAsIndexThroughDay] = (i["height"], i["type"])
            tidesKnown.append((timeAsIndexThroughDay, i["height"], i["type"]))
        else:
            # If not, this tide has been rounded up to midnight (tomorrow)
            # Bump down to 11pm instead (or omit)
            tidesAll[timeAsIndexThroughDay - 1] = (i["height"], i["type"])
            tidesKnown.append((timeAsIndexThroughDay - 1, i["height"], i["type"]))

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
    logging.info(f"Tides Height:\t{tidesMapped}")

    # Start rendering
    epd = display.EPD()
    epd.init()
    epd.Clear()

    canvas = Image.new("1", (epd.width, epd.height), "white")
    draw = ImageDraw.Draw(canvas)

    # Calculate top-left starting position
    startX = offsetX + int((epd.width - (cols * cellSize)) / 2)
    startY = offsetY + int((epd.height - (rows * cellSize)) / 2)

    # Prepare variables
    gridIndex = 0
    itemX = 0
    itemY = 0

    # Traverse through rows top to bottom
    for kk in range(rows):
        # Traverse through cols left to right
        for jj in range(cols):
            cellX = startX + itemX
            cellY = startY + itemY

            # Without tides: unlimited data across full columns
            # dotSize = totalScores[jj]

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

                mappedDotSizeDecay = int(
                    numberToRange(
                        currentRow, startRow, lastRow, maxDotSizeValue, minDotSizeActive
                    )
                )
                dotSize = mappedDotSizeDecay

                # Draw a wind tail line from the edge of the cell to the center, if turned on
                if showWindTail == True:
                    r = cellSize / 2
                    angle = (
                        windDirDataResampled[jj] - 90
                    )  # Offset so 0° is due N and 180° is due S
                    x = r * math.cos(math.radians(angle))
                    y = r * math.sin(math.radians(angle))

                    mappedWindTailWidthDecay = int(
                        numberToRange(currentRow, startRow, lastRow, 3, 1)
                    )

                    draw.line(
                        (
                            (cellX + r + x, cellY + r + y),
                            (cellX + r, cellY + r),
                        ),
                        fill="black",
                        width=mappedWindTailWidthDecay,
                    )

            else:
                # This dot's coordinates are outside the tide height so render as small as possible irrespective of its score
                dotSize = minDotSizeInactive

            # Calculate top-left offset of this dot to center it, according to its size
            dotOffset = int((cellSize - dotSize) / 2)

            # Draw the main dot
            draw.ellipse(
                [
                    (cellX + dotOffset, cellY + dotOffset),
                    (cellX + dotOffset + dotSize, cellY + dotOffset + dotSize),
                ],
                fill="black",
            )

            # Move to the next column in the row
            itemX += cellSize
            # Store what gridIndex we're up to
            gridIndex += 1
        # Go to next row down
        itemY += cellSize
        # Go to first column on left
        itemX = 0

    # Render all of the above to the display
    epd.display(epd.getbuffer(canvas))

    # Put display on pause, keeping what's on screen
    epd.sleep()
    logging.info(f"Finishing printing. Enjoy.")

    # Exit application
    exit()

except IOError as e:
    logging.info(e)

# Exit plan
except KeyboardInterrupt:
    logging.info("Exited.")
    display.epdconfig.module_exit()
    exit()
