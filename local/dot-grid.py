from PIL import Image, ImageDraw
import random
import math

# Display resolution
EPD_WIDTH = 648
EPD_HEIGHT = 480

try:
    canvas = Image.new(
        "1", (EPD_WIDTH, EPD_HEIGHT), 255
    )  # 255: clear the frame
    # Get a drawing context
    draw = ImageDraw.Draw(canvas)

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
            cellX = valueX + offsetX
            cellY = valueY + offsetY

            # Container
            draw.rectangle(
                ((cellX, cellY), (cellX + cellScale, cellY + cellScale)), fill="white")

            # Shape
            # Paint another square within that square at that grid coordinate
            itemScale = random.randrange(2, cellScale)
            itemOffset = int((cellScale - itemScale) / 2)
            draw.ellipse(
                ((cellX + itemOffset, cellY + itemOffset), (cellX + itemOffset + itemScale, cellY + itemOffset + itemScale)), fill="black")

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
