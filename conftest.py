import sys
if sys.version_info[0] == 2:  # shitty workaround for doctests
    from mongoql_conv import InvalidQuery
    InvalidQuery.__name__ = 'mongoql_conv.' + InvalidQuery.__name__

try:
    from django import setup
except ImportError:
    pass
else:
    def pytest_configure():
        setup()

from django.core.management import execute_from_command_line

execute_from_command_line([sys.executable, 'syncdb', '--noinput'])

