#libcappy logger
import logging

# Create a logger object.
logger = logging.getLogger(__name__)

# logger format
logging.basicConfig(
    format='%(asctime)s[%(name)s][%(levelname)s] %(message)s',
    # use 24 hour time format
    datefmt='[%m/%d/%Y][%H:%M:%S]',
    level=logging.INFO,
)

def info(msg):
    logger.info(msg)
def debug(msg):
    logger.debug(msg)
def error(msg):
    logger.error(msg)
def warning(msg):
    logger.warning(msg)

