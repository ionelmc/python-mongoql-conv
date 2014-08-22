try:
    from django import setup
except ImportError:
    pass
else:
    def pytest_configure():
        setup()

import sys
from django.core.management import execute_from_command_line

execute_from_command_line([sys.executable, 'syncdb', '--noinput'])
