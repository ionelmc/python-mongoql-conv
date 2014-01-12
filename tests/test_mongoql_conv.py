import sys
import doctest

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], 'syncdb', '--noinput'])

    results = doctest.testfile('../README.rst', optionflags=doctest.ELLIPSIS|doctest.IGNORE_EXCEPTION_DETAIL)
    print(results)
    if results.failed:
        sys.exit(1)
