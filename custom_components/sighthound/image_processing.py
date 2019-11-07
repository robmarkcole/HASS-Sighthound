"""
Person detection using Sighthound cloud service.
"""
import base64
import io
import os
import json
import requests
from datetime import timedelta

from PIL import Image, ImageDraw
import simplehound.core as hound

import logging
import voluptuous as vol

from homeassistant.core import split_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.components.image_processing import (
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
    ATTR_AGE,
    ATTR_FACES,
    ATTR_GENDER,
    CONF_SOURCE,
    CONF_ENTITY_ID,
    CONF_NAME,
    draw_box,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_API_KEY, CONF_MODE

_LOGGER = logging.getLogger(__name__)

EVENT_FACE_DETECTED = "image_processing.face_detected"
EVENT_PERSON_DETECTED = "image_processing.person_detected"

ATTR_BOUNDING_BOX = "bounding_box"
ATTR_PEOPLE = "people"
CONF_ACCOUNT_TYPE = "account_type"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
DEV = "dev"
PROD = "prod"

RED = (255, 0, 0)

SCAN_INTERVAL = timedelta(days=365)  # NEVER SCAN.

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_ACCOUNT_TYPE, default=DEV): vol.In([DEV, PROD]),
        vol.Optional(CONF_SAVE_FILE_FOLDER): cv.isdir,
    }
)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the platform."""
    save_file_folder = config.get(CONF_SAVE_FILE_FOLDER)
    if save_file_folder:
        save_file_folder = os.path.join(save_file_folder, "")  # If no trailing / add it

    entities = []
    for camera in config[CONF_SOURCE]:
        sighthound = SighthoundEntity(
            config.get(CONF_API_KEY),
            config.get(CONF_ACCOUNT_TYPE),
            save_file_folder,
            camera.get(CONF_ENTITY_ID),
            camera.get(CONF_NAME),
        )
        entities.append(sighthound)
    add_devices(entities)


class SighthoundEntity(ImageProcessingEntity):
    """Create a sighthound entity."""

    def __init__(self, api_key, account_type, save_file_folder, camera_entity, name):
        """Init."""
        super().__init__()
        self._api = hound.cloud(api_key, account_type)
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            camera_name = split_entity_id(camera_entity)[1]
            self._name = "sighthound_{}".format(camera_name)
        self._state = None
        self.faces = []
        self.people = []
        self._state = None
        self._image_width = None
        self._image_height = None
        if save_file_folder:
            self._save_file_folder = save_file_folder

    def process_image(self, image):
        """Process an image."""
        try:
            detections = self._api.detect(image)
            self.faces = hound.get_faces(detections)
            self.people = hound.get_people(detections)
            metadata = hound.get_metadata(detections)
            self._image_width = metadata["image_width"]
            self._image_height = metadata["image_height"]

            self._state = len(self.people)
            if hasattr(self, "_save_file_folder") and self._state > 0:
                self.save_image(image, self.people, self.faces, self._save_file_folder)
            for face in self.faces:
                self.fire_face_detected_event(face)
            for person in self.people:
                self.fire_person_detected_event(person)

        except hound.SimplehoundException as exc:
            _LOGGER.error(str(exc))
            self.faces = []
            self.people = []
            self._image_width = None
            self._image_height = None

    def save_image(self, image, people, faces, directory):
        """Save a timestamped image with bounding boxes around targets."""

        img = Image.open(io.BytesIO(bytearray(image))).convert("RGB")
        draw = ImageDraw.Draw(img)

        for person in people:
            box = hound.bbox_to_tf_style(
                person["boundingBox"], self._image_width, self._image_height
            )
            draw_box(draw, box, self._image_width, self._image_height, color=RED)

        for face in faces:
            age = str(face["age"])
            gender = face["gender"]
            face_description = f"{gender}_{age}"
            bbox = hound.bbox_to_tf_style(
                face["boundingBox"], self._image_width, self._image_height
            )
            draw_box(
                draw,
                bbox,
                self._image_width,
                self._image_height,
                text=face_description,
                color=RED,
            )

        latest_save_path = directory + "{}_latest.jpg".format(self._name)
        img.save(latest_save_path)

    def fire_person_detected_event(self, person):
        """Send event with detected total_persons."""
        self.hass.bus.fire(
            EVENT_PERSON_DETECTED,
            {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_BOUNDING_BOX: hound.bbox_to_tf_style(
                    person["boundingBox"], self._image_width, self._image_height
                ),
            },
        )

    def fire_face_detected_event(self, face):
        """Send event with detected total_persons."""
        self.hass.bus.fire(
            EVENT_FACE_DETECTED,
            {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_BOUNDING_BOX: hound.bbox_to_tf_style(
                    face["boundingBox"], self._image_width, self._image_height
                ),
                ATTR_AGE: face["age"],
                ATTR_GENDER: face["gender"],
            },
        )

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
        return self._state

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
