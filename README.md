# HASS-Sighthound
Home-Assistant custom component for face and person detection with a developer account with [sighthound.com](https://www.sighthound.com/products/cloud). Adds an entity where the state of the entity is the number of `persons` detected in an image. Person and face data are accessible as attributes.

You must register with sighthound to get an api key. The developer tier (free) allows 5000 requests per month, therefor you are advised to set a long `scan_interval` and call the `scan` service when you want to process an image, otherwise you will quickly burn through your 5000 requests as the default scan interval is 10 seconds. [Please read the developer docs](https://www.sighthound.com/docs/cloud/detection/).


Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Add to your Home-Assistant config:
```yaml
image_processing:
  - platform: sighthound
    api_key: your_api_key
    scan_interval: 10000
    source:
      - entity_id: camera.local_file
```
Configuration variables:
- **api_key**: Your developer api key.
- **source**: Must be a camera.

#### Optimising resources
[Image processing components](https://www.home-assistant.io/components/image_processing/) process the image from a camera at a fixed period given by the `scan_interval`. This leads to excessive computation if the image on the camera hasn't changed (for example if you are using a [local file camera](https://www.home-assistant.io/components/camera.local_file/) to display an image captured by a motion triggered system and this doesn't change often). The default `scan_interval` [is 10 seconds](https://github.com/home-assistant/home-assistant/blob/98e4d514a5130b747112cc0788fc2ef1d8e687c9/homeassistant/components/image_processing/__init__.py#L27). You can override this by adding to your config `scan_interval: 10000` (setting the interval to 10,000 seconds), and then call the `scan` [service](https://github.com/home-assistant/home-assistant/blob/98e4d514a5130b747112cc0788fc2ef1d8e687c9/homeassistant/components/image_processing/__init__.py#L62) when you actually want to process a camera image. So in my setup, I use an automation to call `scan` when a new image is available.

## To do
- Add a configurable option to make the state of the entity either the number of `persons` or `faces`.
- Parse the `faces` and `persons` data
