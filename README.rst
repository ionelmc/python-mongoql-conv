===========================
    python-mongoql-conv
===========================

.. image:: https://secure.travis-ci.org/ionelmc/python-mongoql-conv.png?branch=master
    :alt: Build Status
    :target: http://travis-ci.org/ionelmc/python-mongoql-conv

.. image:: https://coveralls.io/repos/ionelmc/python-mongoql-conv/badge.png?branch=master
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-mongoql-conv

.. image:: https://badge.fury.io/py/mongoql-conv.png
    :alt: PYPI Package
    :target: https://pypi.python.org/pypi/mongoql-conv

.. image:: https://d2weczhvl823v0.cloudfront.net/ionelmc/python-mongoql-conv/trend.png
    :alt: Bitdeli badge
    :target: https://bitdeli.com/free


::

    >>> from mongoql_conv import compile_to_func
    >>> compile_to_func({"bubu": {"$gt": 1, '$lt': 2}}).source
    "lambda item: ((item['bubu'] > 1) and (item['bubu'] < 2)) # compiled from {'bubu': {'$gt': 1, '$lt': 2}}"