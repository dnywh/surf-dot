from machine import Pin, SPI
import framebuf
import utime
# from datetime import datetime
import math

import network  # Handles connecting to Wi-Fi
import urequests  # Handles making and servicing network requests

import secrets

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

RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13

# Waveshare stuff
# Forked from Waveshare's Pico ePaper-5.83py


class EPD_5in83(framebuf.FrameBuffer):
    def __init__(self):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)

        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HLSB)
        self.init()

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def send_data2(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte(data)
        self.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        print("e-Paper busy")
        while self.digital_read(self.busy_pin) == 0:  # 1: idle, 0: busy
            self.delay_ms(10)
        print("e-Paper busy release")

    def TurnOnDisplay(self):
        self.send_command(0x12)
        self.delay_ms(100)
        self.ReadBusy()

    def init(self):
        # EPD hardware init start
        self.reset()

        self.send_command(0x01)  # POWER SETTING
        self.send_data(0x07)
        self.send_data(0x07)  # VGH=20V,VGL=-20V
        self.send_data(0x3F)  # VDH=15V
        self.send_data(0x3F)  # VDL=-15V

        self.send_command(0x04)  # POWER ON
        self.delay_ms(100)
        self.ReadBusy()  # waiting for the electronic paper IC to release the idle signal

        self.send_command(0x00)  # PANEL SETTING
        self.send_data(0x1F)  # KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f

        self.send_command(0x61)  # tres
        self.send_data(0x02)  # source 648
        self.send_data(0x88)
        self.send_data(0x01)  # gate 480
        self.send_data(0xE0)

        self.send_command(0x15)
        self.send_data(0x00)

        self.send_command(0x50)  # VCOM AND DATA INTERVAL SETTING
        self.send_data(0x10)
        self.send_data(0x07)

        self.send_command(0x60)  # TCON SETTING
        self.send_data(0x22)
        # EPD hardware init end
        return 0

    def display(self, image):
        if image == None:
            return
        self.send_command(0x13)  # WRITE_RAM
        self.send_data2(image)
        self.TurnOnDisplay()

    def Clear(self, color):
        self.send_command(0x13)  # WRITE_RAM
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(color)
        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x02)  # DEEP_SLEEP_MODE
        self.ReadBusy()
        self.send_command(0x07)
        self.send_data(0xA5)

        self.delay_ms(2000)
        self.module_exit()

# Number to range function for general mapping
# https://www.30secondsofcode.org/python/s/num-to-range


def connect():
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)  # Wait one second before trying again
    ip = wlan.ifconfig()[0]  # Get only IP address
    print(f'Connected on {ip}')  # Print this IP address
    # pico_led.on()  # turn on onboard LED


def numberToRange(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


# Circle function taken from Tony Goodhew:
# https://www.instructables.com/Computer-Graphics-101-With-Pi-Pico-and-Colour-Disp/
def circle(x, y, r, c):
    epd.hline(x - r, y, r * 2, c)
    for i in range(1, r):
        a = int(math.sqrt(r * r - i * i))  # Pythagoras!
        epd.hline(x - a, y + i, a * 2, c)  # Lower half
        epd.hline(x - a, y - i, a * 2, c)  # Upper half


try:
    # Pico swap
    connect()

    print("Checking surf...")

    # Pico swap
    # date = datetime.today().strftime('%Y-%m-%d')
    date = f"{utime.localtime()[0]}-{utime.localtime()[1]}-{utime.localtime()[2]}"
    print(date)

    # Parse surf data
    surfData = urequests.get(
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
        hour = int(i["dateTime"][11] + i["dateTime"][12])
        min = int(i["dateTime"][14] + i["dateTime"][15])
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
    # Tell Python that I want to use the Waveshare ePaper thing as my screen
    epd = EPD_5in83()
    epd.Clear(0x00)
    # Fill the entire screen with white (actually black hex code)
    # epd.fill(0x00)  # TODO: remove, redundant?

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
            # Paint a white square with black (inner) outline at that grid coordinate
            epd.fill_rect(
                (valueX + offsetX), (valueY + offsetY), cellScale, cellScale, 0
            )

            # Paint another square within that square at that grid coordinate
            itemScale = 2
            # itemScale = int(cellScale / 2)  # Since it's radius

            circle((valueX + offsetX), (valueY + offsetY), itemScale, 1)

            # Code if using square
            # Center that square within that cell
            # itemOffsetXY = int((cellScale - itemScale) / 2)
            # epd.fill_rect(
            #     (valueX + offsetX + itemOffsetXY),
            #     (valueY + offsetY + itemOffsetXY),
            #     itemScale,
            #     itemScale,
            #     1,
            # )

            # Move to the next column in the row
            valueX += cellScale
            # Store what gridIndex we're up to
            gridIndex += 1
        # Go to next row down
        valueY += cellScale
        # Go to first column on left
        valueX = 0

    # Render all of the above to screen
    epd.display(epd.buffer)

# Exit plan
# TODO: See if this is redundant in MicroPython
except KeyboardInterrupt:
    print("Exiting...")
    epd.module_exit()
    exit()
