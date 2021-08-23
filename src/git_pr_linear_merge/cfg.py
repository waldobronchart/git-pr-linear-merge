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


class MergeConfig:
    def __init__(self, config):
        self.merge_msg_format = config.get('merge', 'merge_msg_format', fallback=r'Merge: {TITLE} (#{NUMBER})')
        self.always_squash_single_commit_pulls = config.getboolean('merge', 'always_squash_single_commit_pulls', fallback=True)

        self.squash_msg_format = config.get('squash', 'squash_msg_format', fallback=r'{TITLE} (#{NUMBER})')
        self.squash_cmd_enabled = config.getboolean('squash', 'squash_cmd_enabled', fallback=True)
