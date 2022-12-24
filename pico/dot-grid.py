from machine import Pin, SPI
import framebuf
import utime
import random
import math

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


# Circle function taken from Tony Goodhew:
# https://www.instructables.com/Computer-Graphics-101-With-Pi-Pico-and-Colour-Disp/
def circle(x, y, r, c):
    epd.hline(x - r, y, r * 2, c)
    for i in range(1, r):
        a = int(math.sqrt(r * r - i * i))  # Pythagoras!
        epd.hline(x - a, y + i, a * 2, c)  # Lower half
        epd.hline(x - a, y - i, a * 2, c)  # Upper half


try:
    # Tell Python that I want to use the Waveshare ePaper thing as my screen
    epd = EPD_5in83()
    epd.Clear(0x00)

    # Fill the entire screen with white (actually black hex code)
    epd.fill(0x00)

    # Set cols and rows (grid size)
    cols = 24
    rows = 24
    # Set scale for each cell
    cellScale = 16

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
            itemScale = random.randrange(2, cellScale)
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
