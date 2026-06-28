# WhereSun

Home Assistant custom integration that generates a dynamic SVG showing the current sun or moon position and the shadow cast on your house.

Inspired by [clmun/Shadow](https://github.com/clmun/Shadow), but fully configurable from the Home Assistant UI.

## Features

- Mandatory address setup with automatic geocoding
- Visual house builder with draggable and resizable squares/rectangles
- Sun and moon position with realistic shadow rendering
- Sensor with azimuth and elevation attributes
- Camera entity for Lovelace picture cards
- Service `wheresun.generate_svg` to force regeneration

## Installation

### HACS

1. Add this repository as a custom integration in HACS
2. Install **WhereSun**
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for **WhereSun**

### Manual

Copy `custom_components/wheresun` into your Home Assistant `custom_components` folder and restart.

## Setup

1. Enter your house address
2. Build the house footprint with the visual editor
3. Optionally adjust colors and update interval in integration options

## Lovelace example

```yaml
type: picture-entity
entity: camera.wheresun_shadow
```

## Reconfigure house layout

Open the integration, choose **Reconfigure**, then edit the layout in the visual editor.

## Requirements

- Home Assistant 2024.1+
- Internet access for address geocoding (Nominatim)

## Credits

- Original Shadow idea and rendering logic: [clmun/Shadow](https://github.com/clmun/Shadow)
- OpenHAB community for the original concept
