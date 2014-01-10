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

Library to convert those MongoDB queries to something else, like a python
expresion, a function or a Django Q object tree to be used with a ORM query.

compile_to_string
=================


::

    >>> from mongoql_conv import compile_to_string

    >>> compile_to_string({"myfield": 1})
    "row['myfield'] == 1"
    >>> compile_to_string({"myfield": 1}, object_name='item')
    "item['myfield'] == 1"

    >>> compile_to_string({"myfield": {"$in": [1, 2]}})
    "row['myfield'] in {1, 2}"

    >>> compile_to_string({"myfield": {"$in": {1: 2}}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.


Supported operators
-------------------

Arithmetic:

* gt::

    >>> compile_to_string({"myfield": {"$gt": 1}})
    "row['myfield'] > 1"
    >>> compile_to_string({"myfield": {"$gt": [1]}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part [1]. Expected value of type int, float, str, unicode, bool or None.

* gte::

    >>> compile_to_string({"myfield": {"$gte": 1}})
    "row['myfield'] >= 1"

* lt::

    >>> compile_to_string({"myfield": {"$lt": 1}})
    "row['myfield'] < 1"

* lte::

    >>> compile_to_string({"myfield": {"$lte": 1}})
    "row['myfield'] <= 1"

* eq::

    >>> compile_to_string({"myfield": {"$eq": 1}})
    "row['myfield'] == 1"
    >>> compile_to_string({"myfield": 1})
    "row['myfield'] == 1"

* ne::

    >>> compile_to_string({"myfield": {"$ne": 1}})
    "row['myfield'] != 1"

Containers:

* in::

    >>> compile_to_string({"myfield": {"$in": (1, 2, 3)}})
    "row['myfield'] in {1, 2, 3}"

* nin::

    >>> compile_to_string({"myfield": {"$nin": [1, 2, 3]}})
    "row['myfield'] not in {1, 2, 3}"
    >>> compile_to_string({"myfield": {"$nin": {1: 2}}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

* size::

    >>> compile_to_string({"myfield": {"$size": 3}})
    "len(row['myfield']) == 3"
    >>> compile_to_string({"myfield": {"$size": "3"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part '3'. Expected one of: int, long.


* all::

    >>> compile_to_string({"myfield": {"$all": [1, 2, 3]}})
    "set(row['myfield']) == {1, 2, 3}"
    >>> compile_to_string({"myfield": {"$all": 1}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 1. Expected one of: set, list, tuple, frozenset.

Boolean operators:

* or::

    >>> compile_to_string({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]})
    "(row['bubu'] > 1) or (row['bubu'] < 2)"
    >>> compile_to_string({'$or': "invalid value"})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.

* and::

    >>> compile_to_string({'$and':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]})
    "(row['bubu'] > 1) and (row['bubu'] < 2)"
    >>> compile_to_string({'$or': "invalid value"})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.

* *nesting*::

    >>> compile_to_string({'$and': [
    ...     {"bubu": {"$gt": 1}},
    ...     {'$or': [
    ...         {'bubu': {'$lt': 2}},
    ...         {'$and': [
    ...             {'bubu': {'$lt': 3}},
    ...             {'bubu': {'$lt': 4}},
    ...         ]}
    ...     ]}
    ... ]})
    "(row['bubu'] > 1) and ((row['bubu'] < 2) or ((row['bubu'] < 3) and (row['bubu'] < 4)))"

Regular expressions:

* regex::

    >>> compile_to_string({"myfield": {"$regex": 'a'}})
    "re.match('a', row['myfield'], 0)"

    >>> compile_to_string({"bubu": {"$regex": ".*x"}}, object_name='X')
    "re.match('.*x', X['bubu'], 0)"

    >>> closure = {}
    >>> compile_to_string({"bubu": {"$regex": ".*x"}}, closure=closure), closure
    ("var0.match(row['bubu']", {'var0': "re.compile('.*x', 0)"})

    >>> compile_to_string({"myfield": {"$regex": 'junk('}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid regular expression 'junk(': unbalanced parenthesis

    >>> compile_to_string({"myfield": {"$regex": 'a', 'junk': 'junk'}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part "'junk'". You can only have `$options` with `$regex`.

    >>> compile_to_string({"bubu": {"$regex": ".*", "$options": "junk"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'junk'. Unsupported regex option 'j'. Only 's', 'x', 'm', 'i' are supported !

    >>> compile_to_string({"bubu": {"$options": "i"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {'$options': 'i'}. Cannot have $options without $regex.

