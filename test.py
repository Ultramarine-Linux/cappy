import yaml
from libcappy.installer import Bootstrap

bootstrapper = Bootstrap(config='example.yml')
print(bootstrapper.phase_1('build/'))