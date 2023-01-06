# Surf Grid

![Surf Grid Sequence.gif](https://res.cloudinary.com/dannywhite/image/upload/v1672986915/github/surf-grid-sequence.gif)

Surf Grid is a [Pi Frame](https://github.com/dnywh/pi-frame) app. It prints an abstract surf report in the style of [Kōhei Sugiura](https://w.wiki/69Lz) to an e-ink display via Raspberry Pi.

Surf Grid relies on the [WillyWeather API](https://www.willyweather.com.au/info/api.html) for location-specific wind, tide, and swell forecast data.

## Prerequisites

To run Surf Grid you need to first:

1. Join a Wi-Fi network on your Raspberry Pi
2. Enable SSH on your Raspberry Pi
3. Plug in a Waveshare e-Paper or similar display to your Raspberry Pi

Surf Grid works great with [Pi Frame](https://github.com/dnywh/pi-frame), which includes the Waveshare drivers amongst other things like a scheduling template. If you’d prefer not to use Pi Frame, you’ll need to upload the [Waveshare e-Paper display drivers](https://github.com/waveshare/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd) (or similar) to your Raspberry Pi in a _lib_ directory that is a sibling of Surf Grid’s. Here's an example:

```
.
└── surf-grid
└── lib
    └── waveshare_epd
        ├── __init__.py
        ├── epdconfig.py
        └── epd5in83_V2
```

Either way, Waveshare displays require some additional setup. See the [Hardware Connection](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual#Hardware_Connection) and [Python](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual#Python) sections of your model’s manual.

## Get started

If you haven’t already, copy all the contents of this Surf Grid repository over to the main directory of your Raspberry Pi.

### Set the display driver

Look for this line as the last import in _[app.py](https://github.com/dnywh/surf-grid/blob/main/app.py)_:

```python
from waveshare_epd import epd5in83_V2 as display
```

Swap out the `epd5in83_V2` for your Waveshare e-Paper display driver, which should be in the _lib_ directory. Non-Waveshare displays should be imported here too, although you’ll need to make display-specific adjustments in the handful of places `display` is called further on.

### Install required packages

See _[requirements.txt](https://github.com/dnywh/surf-grid/blob/main/requirements.txt)_ for a short list of required packages. Install each package on your Raspberry Pi using `sudo apt-get`. Here’s an example:

```bash
sudo apt-get update
sudo apt-get install python3-pil
sudo apt-get install python3-requests
sudo apt-get install python3-scipy
```

### Enter your WillyWeather credentials

Fill out an *env.py* file in the Surf Grid directory with your [WillyWeather API key](https://www.willyweather.com.au/account/api.html). An example is provided in [_env.example.py_](https://github.com/dnywh/surf-grid/blob/main/env.example.py).

### Run the app

Run Surf Grid just like you would any other Python file on a Raspberry Pi:

```bash
cd surf-grid
python3 app.py
```

Surf Grid is noisy by default. Look for the results in Terminal.

---

## Usage

### Run on a schedule

See [Pi Frame](https://github.com/dnywh/pi-frame) for a crontab template and usage instructions.

### Design options

Surf Grid contains several visual design parameters in _[app.py](https://github.com/dnywh/surf-grid/blob/main/app.py)_.

| Option         | Type    | Description                                                                                                             |
| -------------- | ------- | ----------------------------------------------------------------------------------------------------------------------- |
| `showWindTail` | Boolean | Shows a visual of the wind direction. Note that the wind direction is taken into account for the `dotSize` calculation. |
| `hourStart`    | Integer | An hour of the day. Sets the first column of the grid.                                                                  |
| `hourEnd`      | Integer | A later hour of the day. Sets the last column of the grid.                                                              |
| `cols`         | Integer | The amount of columns between (and including) `hourStart` and `hourEnd`.                                                |

Several more design option variables exist to affect dot size and grid composition.

### Location options

Surf Grid defaults to Coolum Beach, Queensland, Australia. Given that beach on the east coast of Australia, Surf Grid determines westerly winds as favourable offshore winds and easterly winds as poor onshore winds. Here’s where that parameter is passed, amongst other location-specific parameters:

| Option                       | Type    | Description                                                                                                                                               |
| ---------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `locationId`                 | Integer | Sets where the surf forecast is for. See the [API documentation](https://www.willyweather.com.au/api/docs/v2.html#search) for finding your location’s ID. |
| `locationMaxTideHeight`      | Integer | Maximum tide height for that location in metres. Affects how tall tides are drawn.                                                                        |
| `locationMaxSwellHeight`     | Integer | Maximum swell height for that location in metres. Affects `dotSize`.                                                                                      |
| `locationWindDirRangeStart`  | Integer | Start degree (going clockwise) for optimal wind origin. Affects `dotSize`.                                                                                |
| `locationWindDirRangeEnd`    | Integer | End degree (going clockwise) for optimal wind origin. Affects `dotSize`.                                                                                  |
| `locationWindDirRangeBuffer` | Integer | A buffer range on either end for minimal `dotSize` scoring.                                                                                               |

### Save to folder

Surf Grid contains an `exportImages` boolean option in _[app.py](https://github.com/dnywh/surf-grid/blob/main/app.py)._ When `True` it saves both an image and text file to a timestamped directory within an _exports_ directory.
