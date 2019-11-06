# HASS-Sighthound
Home Assistant custom component for person & face detection with [Sighthound Cloud](https://www.sighthound.com/products/cloud). To use Sighthound Cloud you must register with Sighthound to get an api key. The Sighthound Developer tier (free for non-commercial use) allows 5000 requests per month. If you need more requests per month you will need to sign up for a production account (i.e. Basic or Pro account). 

This component adds an image processing entity where the state of the entity is the number of `people` detected in an image. The number of `faces` are exposed as an attribute of the sensor. Note that whenever a face is detected in an image, a person is always detected. However a person can be detected without a face being detected (e.g. if they have their back to the camera). Note that in order to prevent accidental over-billing, the component will not scan images automatically, but requires you to call the `image_processing.scan` service. This behaviour can be changed by configuring a `scan_interval`, shown below.

Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder). Add to your Home-Assistant config:

```yaml
image_processing:
  - platform: sighthound
    api_key: your_api_key
    scan_interval: 30 # optional, in seconds
    source:
      - entity_id: camera.local_file
```

Configuration variables:
- **api_key**: Your developer api key.
- **account_type**: (Optional, default `dev` for Developer) If you have a paid account, used `prod`.
- **source**: Must be a camera.

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Sighthound/blob/master/images/usage.jpg" width="750">
</p>

<p align="center">
<img src="https://github.com/robmarkcole/HASS-Sighthound/blob/master/images/people_identified.jpg" width="750">
</p>
