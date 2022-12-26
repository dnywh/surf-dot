# Surf Dot

Use your Pi and Waveshare ePaper/e-ink display to show the day's surf report in the style of Kōhei Sugiura:

![Kōhei Sugiura's stamps for the 1972 Olympics](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Stamps_of_Germany_%28BRD%29%2C_Olympiade_1972%2C_Blockausgabe_1971%2C_Markenblock.jpg/1600px-Stamps_of_Germany_%28BRD%29%2C_Olympiade_1972%2C_Blockausgabe_1971%2C_Markenblock.jpg?20070622084910)
_Image source: [Wikimedia commons](https://w.wiki/69Lz)_

## What do I need to get started?

You can run the [local](/src/local) version with only:

- A [Willy Weather API](https://www.willyweather.com.au/info/api.html) key

To make a nice picture frame display you also need:

- A Raspberry Pi Zero W or better
- A Waveshare ePaper display

## How do I customise the surf report location?

Surf Dot is set to Coolum Beach, Qld, Australia.

First you'll need to [search](https://www.willyweather.com.au/api/docs/v2.html#search) Willy Weather for the `id` of the coastal location that you'd like to base your surf report off. Then replace the value of `locationId` in [app.py](/src/zero/app.py) to this new `id`.

You should also tweak the other `location` parameters to match your local area's conditions, such as the offshore wind range and maximum swell height.

## Can I run this on a Pico W?

In my experience, you can only select two of the following features before an app gets too big for the Pico W:

- Loop through lists to create a data visualisation
- Use real-world data via an API
- Render this to an attached display

Surf Dot unfortunately needs all three.

See [this gist](https://gist.github.com/dnywh/7a56db9b077843e5926ff594c7ecd375) instead for a Pico W artwork generator based on Kōhei Sugiura's work. It's essentially Surf Dot with random data.

If you still want to try getting this to run on the Pico, feel free to start from my [last commit](https://github.com/dnywh/surf-dot/blob/ac531aa3aa59acd1ebbf5a066347d1437d4da284/src/pico/app.py) before giving up. Please reach out if you get it to work.
