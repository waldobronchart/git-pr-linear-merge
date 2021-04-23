import logging

logger = logging.getLogger()

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    _grey = '\x1b[38;21m'
    _yellow = '\x1b[33;21m'
    _red = '\x1b[31;21m'
    _bold_red = '\x1b[31;1m'
    _reset = '\x1b[0m'
    _format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'

    FORMATS = {
        logging.DEBUG: f'{_grey}> %(message)s {_reset}',
        logging.INFO: f'| %(message)s',
        logging.WARNING: f'{_yellow}Warning: %(message)s{_reset}',
        logging.ERROR: f'{_red}Error: %(message)s{_reset}',
        logging.CRITICAL: f'{_bold_red}Fatal: %(message)s{_reset}',
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging(level):
    global logger
    logger.setLevel(level)
    logger_streamhandler = logging.StreamHandler()
    logger_streamhandler.setFormatter(CustomFormatter())
    logger.addHandler(logger_streamhandler)