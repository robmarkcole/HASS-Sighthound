# HASS-Sighthound
Home Assistant custom component for face and person detection with [sighthound.com](https://www.sighthound.com/products/cloud). Adds an entity where the state of the entity is the number of `faces` detected in an image. Person and face data are accessible as attributes. You must register with sighthound to get an api key. The developer tier (free) allows 5000 requests per month. Note that in order to prevent accidental over-billing, the component will not scan images automatically, but requires you to call the `image_processing.scan` service. This behaviour can be changed by configuring a `scan_interval` [as described in the docs](https://www.home-assistant.io/components/image_processing#scan_interval-and-optimising-resources).

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: sighthound
    api_key: your_api_key
    mode: dev
    state_display: persons
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **api_key**: Your developer api key.
- **mode**: (Optional, default `dev`) If you have a paid account, used `prod`.
- **state_display**: (Optional, default `faces`) Select `persons` if you wish the state to be the number of persons in an image.
- **source**: Must be a camera.

## Events
On each image processing, an `image_processing.detect_face` event is fired for each detected face, and an `image_processing.detect_persons` event is fired with the total number of detected persons. The events can be used to trigger automations, for example the following:

```yaml
- id: '11200961111'
  alias: Notify on person detection
  trigger:
    platform: event
    event_type: image_processing.detect_persons
  action:
    service: notify.pushbullet
    data_template:
      title: People detected
      message: 'Alert: {{ trigger.event.data.total_persons }} persons detected by {{ trigger.event.data.entity_id }}'
```

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Sighthound/blob/master/images/usage.jpg" width="750">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Sighthound/blob/master/images/people_identified.jpg" width="750">
</p>
The image with bounding boxes is just to show what the component is recognising. If you are curious how to view bounding boxes [see this repo](https://github.com/robmarkcole/Useful-python/blob/master/Sighthound/Sighthound.ipynb).
