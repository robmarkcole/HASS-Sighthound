"""
Person detection using Sighthound cloud service.
"""
import io
import logging
import os

from PIL import Image, ImageDraw

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import simplehound.core as hound
import voluptuous as vol
from homeassistant.components.image_processing import (
    ATTR_AGE,
    ATTR_FACES,
    ATTR_GENDER,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_SOURCE,
    PLATFORM_SCHEMA,
    ImageProcessingEntity,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_API_KEY, CONF_FILE_PATH, CONF_MODE
from homeassistant.core import split_entity_id
from homeassistant.util.pil import draw_box

_LOGGER = logging.getLogger(__name__)

EVENT_FACE_DETECTED = "sighthound.face_detected"
EVENT_PERSON_DETECTED = "sighthound.person_detected"
EVENT_FILE_SAVED = "sighthound.file_saved"

ATTR_BOUNDING_BOX = "bounding_box"
ATTR_PEOPLE = "people"
CONF_ACCOUNT_TYPE = "account_type"
CONF_SAVE_FILE_FOLDER = "save_file_folder"
CONF_SAVE_TIMESTAMPTED_FILE = "save_timestamped_file"
DEV = "dev"
PROD = "prod"

DATETIME_FORMAT = "%Y-%m-%d_%H:%M:%S"

RED = (255, 0, 0)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_ACCOUNT_TYPE, default=DEV): vol.In([DEV, PROD]),
        vol.Optional(CONF_SAVE_FILE_FOLDER): cv.isdir,
        vol.Optional(CONF_SAVE_TIMESTAMPTED_FILE, default=False): cv.boolean,
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
            config.get(CONF_SAVE_TIMESTAMPTED_FILE),
            camera.get(CONF_ENTITY_ID),
            camera.get(CONF_NAME),
        )
        entities.append(sighthound)
    add_devices(entities)


class SighthoundEntity(ImageProcessingEntity):
    """Create a sighthound entity."""

    def __init__(
        self,
        api_key,
        account_type,
        save_file_folder,
        save_timestamped_file,
        camera_entity,
        name,
    ):
        """Init."""
        super().__init__()
        self._api = hound.cloud(api_key, account_type)
        self._camera = camera_entity
        if name:
            self._name = name
        else:
            self._camera_name = split_entity_id(camera_entity)[1]
            self._name = "sighthound_{}".format(self._camera_name)
        self._state = None
        self.faces = []
        self.people = []
        self._state = None
        self._last_detection = None
        self._image_width = None
        self._image_height = None
        if save_file_folder:
            self._save_file_folder = save_file_folder
        self._save_timestamped_file = save_timestamped_file

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
            if self._state > 0:
                self._last_detection = dt_util.now().strftime(DATETIME_FORMAT)
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
        out_file = open(latest_save_path, "wb")
        img.save(out_file, format="JPEG")
        out_file.flush()
        os.fsync(out_file)
        out_file.close()
        self.fire_saved_file_event(latest_save_path)

        if self._save_timestamped_file:
            timestamp_save_path = directory + "{} {}.jpg".format(
                self._name, self._last_detection
            )

            out_file = open(timestamp_save_path, "wb")
            img.save(out_file, format="JPEG")
            out_file.flush()
            os.fsync(out_file)
            out_file.close()
            self.fire_saved_file_event(timestamp_save_path)
            _LOGGER.info("Saved %s", timestamp_save_path)

    def fire_saved_file_event(self, save_path):
        """Fire event when saving a file"""
        self.hass.bus.fire(
            EVENT_FILE_SAVED,
            {ATTR_ENTITY_ID: self.entity_id, CONF_FILE_PATH: save_path},
        )

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
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ATTR_PEOPLE

    @property
    def device_state_attributes(self):
        """Return the classifier attributes."""
        attr = {
            ATTR_FACES: len(self.faces),
        }
        if self._last_detection:
            attr["last_person"] = self._last_detection
        return attr
