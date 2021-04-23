import os
import configparser
from . import logger

RC_FILE_NAME = '.linmergerc'
log = logger.logger

def write_default_config(auth_token):
    config = configparser.ConfigParser()
    config['auth'] = {
        'github_access_token': auth_token
    }

    config_file_path = os.path.expanduser(f'~/{RC_FILE_NAME}')
    log.debug(f'Writing default config to {config_file_path}')
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)