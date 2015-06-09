import os
import json


class Config:
    _overrides = {}
    _mode = 'prod'
    config = None

    @classmethod
    def set_mode(self, mode):
        self._mode = mode

    @classmethod
    def set_overrides(self, overrides):
        self._overrides = overrides

    @classmethod
    def load_config(cls):
        if cls.config is not None:
            return cls.config

        # if a config file is not specified in the environment
        if 'FLEXAPI_CONFIG_FILE' not in os.environ:
            cls.config = {}
            return cls.config

        # make sure specified file exists
        file = os.path.normpath(os.environ['FLEXAPI_CONFIG_FILE'])
        if not os.path.isfile(file):
            raise Exception('Config file not found')

        try:
            fd = open(file, 'r')
        except IOError:
            raise Exception('Error reading config file')

        try:
            config = json.load(fd)
        except Exception as e:
            raise Exception('Error parsing config file: ' + str(e))

        if type(config) != dict:
            raise Exception('Error parsing config file')

        cls.config = config
        return cls.config

    @classmethod
    def get(cls, item):
        config = cls.load_config()

        if cls._mode != 'prod':
            config.update(cls._overrides)

        pos = item.find('.')
        if pos > 0:
            k1 = item[:pos]
            k2 = item[pos + 1:]

            # read config from environment
            k = '_'.join([k1, k2]).upper()
            if k in os.environ:
                if k1 not in config:
                    config[k1] = {}
                config[k1][k2] = os.environ[k]

            return config.get(k1, {}).get(k2)

        # read config from environment
        prefix = item.upper() + '_'
        prefix_len = len(prefix)

        for (k, v) in os.environ.iteritems():
            if not k.startswith(prefix):
                continue

            if item not in config:
                config[item] = {}
            config[item][k[prefix_len:].lower()] = v

        return config.get(item)

# end of script
