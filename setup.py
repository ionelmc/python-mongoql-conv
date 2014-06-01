# -*- encoding: utf8 -*-
from setuptools import setup, find_packages

import os

setup(
    name="mongoql-conv",
    version="0.4.1",
    url='https://github.com/ionelmc/python-mongoql-conv',
    download_url='',
    license='BSD',
    description="Library to convert those MongoDB queries to something else, like a python "
                "expresion, a function or a Django Q object tree to be used with a ORM query.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    author='Ionel Cristian Mărieș',
    author_email='contact@ionelmc.ro',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    keywords=['mongo', 'mongodb', 'django', 'orm', 'query', 'conversion', 'converter'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Utilities',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=[
        'six',
    ],
    extras_require={
        'django': [
            'Django',
        ]
    }
)
