[![Sponsor](https://img.shields.io/badge/sponsor-%F0%9F%92%96-green)](https://github.com/sponsors/robmarkcole)

**Note** that there is [an official integration for Sighthound](https://www.home-assistant.io/integrations/sighthound/), but this version adds experimental features to allow saving of processed images.

# HASS-Sighthound
[Home Assistant](https://www.home-assistant.io/) custom component for people detection with [Sighthound Cloud](https://www.sighthound.com/products/cloud). To use Sighthound Cloud you must register with Sighthound to get an api key. The Sighthound Developer tier (free for non-commercial use) allows 5000 requests per month. If you need more requests per month you will need to sign up for a production account (i.e. Basic or Pro account).

This component adds an image processing entity where the state of the entity is the number of `people` detected in an image. The number of `faces` are exposed as an attribute of the sensor. Note that whenever a face is detected in an image, a person is **always** detected. However a person can be detected without a face being detected (e.g. if they have their back to the camera). The time of the last detected person is in the `last_person` attribute.

If `save_file_folder` is configured, on each new detection of a person an annotated image with the name `sighthound_latest.jpg` is saved in the configured folder if it doesnt already exist, and over-written if it does exist. The `sighthound_latest.jpg` image shows the bounding box around detected people and can be displayed on the Home Assistant front end using a local_file camera, and used in notifications. Additionally, if `save_timestamped_file` is configred as `True` then an image file is created of the processed image, where the file name includes the time of detection. When either of these images are saved an `sighthound.file_saved` event is fired, allowing the image to be used in a notification. It is the users responsibility to manage these files, e.g. using an automation to clean up files older than some time.

For each person detected, an `sighthound.person_detected` event is fired. The event data includes the `entity_id` of the image processing entity firing the event, and the bounding box around the detected person. Similarly, for each face detected an `sighthound.face_detected` event is fired, which in addition to the bounding box and entity_id contains the `age` and `gender` of the face. To see these events in your logs, configure the logger level to `debug`.

**Note** that in order to prevent accidentally using up your requets to Sighthound, by default the component will **not** automatically scan images, but requires you to call the `image_processing.scan` service e.g. using an automation triggered by motion. Alternativley, periodic scanning can be enabled by configuring a `scan_interval`.

## Installation

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: sighthound
    api_key: your_api_key
    save_file_folder: /config/www/
    save_timestamped_file: True
    # scan_interval: 30 # optional, in seconds
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **api_key**: Your developer api key.
- **account_type**: (Optional, default `dev` for Developer) If you have a paid account, used `prod`.
- **save_file_folder**: (Optional) The folder to save processed images to. Note that folder path should be added to [whitelist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/)
- **save_timestamped_file**: (Optional, default `False`, requires `save_file_folder` to be configured) Save the processed image with the time of detection in the filename.
- **source**: Must be a camera.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Sighthound/blob/master/images/usage.png" width="500">
</p>

## Displaying the `sighthound_latest.jpg` image
It is easy to display the `sighthound_latest.jpg` image with a [local_file](https://www.home-assistant.io/integrations/local_file) camera. An example configuration is:

```yaml
camera:
  - platform: local_file
    file_path: /config/www/sighthound_latest.jpg
    name: sighthound
```

## Automation to send the processed image in a notification
We can use a notification platform such as [Telegram](https://www.home-assistant.io/integrations/telegram/) to send a message including the processed image.

```yaml
- action:
  - data_template:
      caption: "Person detected by Sighthound"
      file: "{{trigger.event.data.file_path}}"
    service: telegram_bot.send_photo
  alias: New person alert
  condition: []
  id: 'persondetectedautomation'
  trigger:
  - platform: event
    event_type: sighthound.file_saved
  ```

## Count people using the `sighthound.person_detected` event
Using a [counter](https://www.home-assistant.io/integrations/counter) an automation can be used to count the number of people seen. In `configuration.yaml`:

```yaml
counter:
  people_counter:
    name: People
    icon: mdi:alert
```

In `automations.yaml`:
```yaml
- id: 'peoplecounterautomation'
  alias: People Counting Automation
  trigger:
    platform: event
    event_type: sighthound.person_detected
    event_data:
      entity_id: image_processing.sighthound_local_file
  action:
    service: counter.increment
    entity_id: counter.people_counter
```

The counter is incremented each time a person is detected. The bounding box can in principle be used to include/exclude people based on their location in the image. TODO: add example of using bounding box.

## Info on the bounding box
The bounding boxes are formatted to be consumed by the `image_processing.draw_box()` function. The formatting convention is [identical](https://www.tensorflow.org/api_docs/python/tf/image/draw_bounding_boxes) to that used by Tensorflow, where the bounding box is defined by the tuple `(y_min, x_min, y_max, x_max)` where the coordinates are floats in the range `[0.0, 1.0]` and relative to the width and height of the image.

## ✨ Support this work

https://github.com/sponsors/robmarkcole

If you or your business find this work useful please consider becoming a sponsor at the link above, this really helps justify the time I invest in maintaining this repo. As we say in England, 'every little helps' - thanks in advance! 