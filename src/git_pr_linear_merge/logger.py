import logging
from colorama import Fore, Back, Style

logger = logging.getLogger()

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    FORMATS = {
        logging.DEBUG: f'{Style.DIM}> %(message)s {Style.RESET_ALL}',
        logging.INFO: f'| %(message)s',
        logging.WARNING: f'{Fore.YELLOW}{Style.BRIGHT}Warning:{Style.NORMAL} %(message)s{Style.RESET_ALL}',
        logging.ERROR: f'{Fore.RED}{Style.BRIGHT}Error:{Style.NORMAL} %(message)s{Style.RESET_ALL}',
        logging.CRITICAL: f'{Fore.RED}{Style.BRIGHT}Fatal:{Style.NORMAL} %(message)s{Style.RESET_ALL}',
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