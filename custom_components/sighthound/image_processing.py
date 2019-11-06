"""
Search images for people and faces using Sighthound cloud service.
"""
import base64
import json
import requests
from datetime import timedelta

import simplehound.core as hound

import logging
import voluptuous as vol

from homeassistant.core import split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
    ATTR_FACES,
    ATTR_GENDER,
    CONF_SOURCE,
    CONF_ENTITY_ID,
    CONF_NAME,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_API_KEY, CONF_MODE

_LOGGER = logging.getLogger(__name__)

EVENT_PERSON_DETECTED = "image_processing.person_detected"

ATTR_BOUNDING_BOX = "bounding_box"
ATTR_PEOPLE = "people"
CONF_ACCOUNT_TYPE = "account_type"
DEV = "dev"
PROD = "prod"

SCAN_INTERVAL = timedelta(days=365)  # NEVER SCAN.

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_ACCOUNT_TYPE, default=DEV): vol.In([DEV, PROD]),
    }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the platform."""
    entities = []
    for camera in config[CONF_SOURCE]:
        sighthound = SighthoundEntity(
            config[CONF_API_KEY],
            config[CONF_ACCOUNT_TYPE],
            camera[CONF_ENTITY_ID],
            camera.get(CONF_NAME),
        )
        entities.append(sighthound)
    add_devices(entities)


class SighthoundEntity(ImageProcessingEntity):
    """Create a sighthound entity."""

    def __init__(self, api_key, account_type, camera_entity, name):
        """Init."""
        super().__init__()
        self._api = hound.cloud(api_key, account_type)
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "sighthound {}".format(camera_name)
        self._state = None
        self.metadata = []
        self.faces = []
        self.people = []

    def process_image(self, image):
        """Process an image."""
        try:
            detections = self._api.detect(image)
            self.metadata = hound.get_metadata(detections)
            self.faces = hound.get_faces(detections)
            self.people = hound.get_people(detections)
        except hound.SimplehoundException as exc:
            _LOGGER.error(str(exc))
            self.metadata = []
            self.faces = []
            self.people = []

    @property
    def camera_entity(self):
        """Return camera entity id from process pictures."""
        return self._camera

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return len(self.people)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ATTR_PEOPLE

    @property
    def device_state_attributes(self):
        """Return the classifier attributes."""
        return {
            ATTR_FACES: len(self.faces),
        }
