import sys
from distutils.version import StrictVersion

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
from django import get_version

django_version = get_version()
if StrictVersion(django_version) < StrictVersion('1.9'):
    execute_from_command_line([sys.executable, 'syncdb', '--noinput'])
else:
    execute_from_command_line([sys.executable, 'migrate', '--run-syncdb', '--noinput'])

