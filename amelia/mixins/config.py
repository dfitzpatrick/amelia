import os
from atomicwrites import atomic_write
import json
import collections
import logging
import typing

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', 'static'))
FILE_PATH = os.path.normpath(f'{BASE_DIR}/settings.json')

log = logging.getLogger(__name__)

class ConfigMixin:
    """Mixin that will help aid adding configuration parameters
    that can be easily serialized to disk
    """
    def __init__(self):
        super(ConfigMixin, self).__init__()
        self._config = collections.defaultdict(dict)
        self.parent_key = str(self.__class__.__name__)
        self.config_settings = collections.defaultdict(dict)

        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)

        if not os.path.exists(FILE_PATH):
            self._config[self.parent_key] = {}

        self._load_configuration()



    def _load_configuration(self) -> None:
        """
        Reloads the configuration into the main dictionary object
        Parameters
        ----------
        path

        Returns
        -------

        """
        try:
            with open(FILE_PATH, 'r') as f:
                self._config = json.load(f)
            if not self.config_settings:
                self.config_settings = self._config[self.parent_key]

        except KeyError:
            pass

        except IOError:
            # File does not exist
            with atomic_write(FILE_PATH, overwrite=True) as f:
                self._config[self.parent_key] = {}
                json.dump(self._config, f)

    def save_settings(self):
        """
        Persists the settings to disk
        Returns
        -------

        """
        # Read in the most recent contents in case another process altered.
        self._load_configuration()
        self._config[self.parent_key] = self.config_settings
        log.debug(f'mixin config: {self.config_settings}')

        # Write out the updated contents
        with atomic_write(FILE_PATH, overwrite=True) as f:
            json.dump(self._config, f)















