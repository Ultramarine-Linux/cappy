import yaml
from libcappy.installer import Bootstrap
import libcappy.logger as logger
logger.logger.setLevel(logger.logging.DEBUG)
bootstrapper = Bootstrap(config='example.yml')
#print(bootstrapper.phase_1('build/'))
#bootstrapper.phase_2('build/')
bootstrapper.phase_3('build/')