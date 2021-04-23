import requests
from . import logger
from . import cfg

log = logger.logger


def _test_github_auth_token(token):
    try:
        r = requests.get("https://api.github.com", headers={'Authorization': f'token {token}'})
        log.debug('Github authentication succeeded')
        return r.ok
    except Exception as e:
        log.error(e)
        return False


def _new_auth_setup():
    # Ask if user wants to setup auth now
    auth_now_answer = input(f"Do you want to (re)authenticate now? (y/n) ") or "n"
    if auth_now_answer.lower() == 'y':
        log.info('Go to https://github.com/settings/tokens and generate a new access token (repo, user)')
        entered_access_token = None
        while not entered_access_token:
            entered_access_token = input(f"Enter the Github Access Token: ") or None
            if not entered_access_token:
                log.error('Not a valid token. Please try again')
            elif not _test_github_auth_token(entered_access_token):
                log.error('Github authentication failed, did you enter the correct token?')
                entered_access_token = None
            else:
                cfg.write_default_config(entered_access_token)
                return entered_access_token
    else:
        log.info('Ok. To setup authentication manually, follow these steps:\n'
            + '  1. Go to https://github.com/settings/tokens and generate a new access token (repo, user)\n'
            +f'  2. Create a `{cfg.RC_FILE_NAME}` in your home directory (`~/{cfg.RC_FILE_NAME}`) with the following contents:\n'
            + '     [auth]\n'
            + '     github_access_token = YOUR_GITHUB_ACCESS_TOKEN\n'
            + '  3. Re-run this script to try again'
        )
        exit(1)


def initial_auth_flow_if_necessary(github_access_token=None):
    if not github_access_token:
        log.error('Could not authenticate because no access token was specified or previously saved.')
        return _new_auth_setup()

    elif not _test_github_auth_token(github_access_token):
        log.error('Github authentication failed')
        return _new_auth_setup()

    return github_access_token