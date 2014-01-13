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

For now, only supports flat operations. No subdocuments. It might work but results are undefined/buggy. *Could be fixed
though ...*

Installation
============

::

    pip install mongoql-conv

Or::

    pip install mongoql-conv[django]

API
===

* ``mongoql_conv.to_string``: to_string_
* ``mongoql_conv.to_func``: to_func_
* ``mongoql_conv.django.to_Q``: to_Q_


to_string
=========

::

    >>> from mongoql_conv import to_string

    >>> to_string({"myfield": 1})
    "row['myfield'] == 1"

    >>> to_string({})
    'True'

    >>> to_string({"field1": 1, "field2": 2})
    "(row['field2'] == 2) and (row['field1'] == 1)"

    >>> to_string({"myfield": 1}, object_name='item')
    "item['myfield'] == 1"

    >>> to_string({"myfield": {"$in": [1, 2]}})
    "row['myfield'] in {1, 2}"

    >>> to_string({"myfield": {"$in": {1: 2}}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

    >>> to_string({"myfield": {"$and": []}})
    'True'

Supported operators
-------------------

Arithmetic
``````````

* **$gt**::

    >>> to_string({"myfield": {"$gt": 1}})
    "row['myfield'] > 1"
    >>> to_string({"myfield": {"$gt": [1]}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part [1]. Expected value of type int, float, str, unicode, bool or None.

* **$gte**::

    >>> to_string({"myfield": {"$gte": 1}})
    "row['myfield'] >= 1"

* **$lt**::

    >>> to_string({"myfield": {"$lt": 1}})
    "row['myfield'] < 1"

* **$lte**::

    >>> to_string({"myfield": {"$lte": 1}})
    "row['myfield'] <= 1"

* **$eq**::

    >>> to_string({"myfield": {"$eq": 1}})
    "row['myfield'] == 1"
    >>> to_string({"myfield": 1})
    "row['myfield'] == 1"

* **$ne**::

    >>> to_string({"myfield": {"$ne": 1}})
    "row['myfield'] != 1"

* **$mod**::

    >>> to_string({"myfield": {"$mod": [2, 1]}})
    "row['myfield'] % 2 == 1"
    >>> to_string({"myfield": {"$mod": [2, 1, 3]}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part [2, 1, 3]. You must have two items: divisor and remainder.
    >>> to_string({"myfield": {"$mod": 2}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 2. Expected one of: list, tuple.
    >>> to_string({"myfield": {"$mod": (2, 1)}})
    "row['myfield'] % 2 == 1"

Containers
``````````

* **$in**::

    >>> to_string({"myfield": {"$in": (1, 2, 3)}})
    "row['myfield'] in {1, 2, 3}"

* **$nin**::

    >>> to_string({"myfield": {"$nin": [1, 2, 3]}})
    "row['myfield'] not in {1, 2, 3}"
    >>> to_string({"myfield": {"$nin": {1: 2}}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

* **$size**::

    >>> to_string({"myfield": {"$size": 3}})
    "len(row['myfield']) == 3"
    >>> to_string({"myfield": {"$size": "3"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part '3'. Expected one of: int, long.


* **$all**::

    >>> to_string({"myfield": {"$all": [1, 2, 3]}})
    "set(row['myfield']) >= {1, 2, 3}"
    >>> to_string({"myfield": {"$all": 1}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 1. Expected one of: set, list, tuple, frozenset.

* **$exists**::

    >>> to_string({"myfield": {"$exists": True}})
    "'myfield' in row"
    >>> to_string({"myfield": {"$exists": False}})
    "'myfield' not in row"

Boolean operators
`````````````````

* **$or**::

    >>> to_string({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]})
    "(row['bubu'] > 1) or (row['bubu'] < 2)"
    >>> to_string({'$or': "invalid value"})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.

* **$and**::

    >>> to_string({'$and':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]})
    "(row['bubu'] > 1) and (row['bubu'] < 2)"
    >>> to_string({'$or': "invalid value"})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.

* **$*nesting***::

    >>> to_string({'$and': [
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

Regular expressions
```````````````````

* **$regex**::

    >>> to_string({"myfield": {"$regex": 'a'}})
    "re.match('a', row['myfield'], 0)"

    >>> to_string({"bubu": {"$regex": ".*x"}}, object_name='X')
    "re.match('.*x', X['bubu'], 0)"

    >>> to_string({"myfield": {"$regex": 'a', "$options": 'i'}})
    "re.match('a', row['myfield'], 2)"

    >>> closure = {}
    >>> to_string({"bubu": {"$regex": ".*x"}}, closure=closure), closure
    ("var0.match(row['bubu'])", {'var0': "re.compile('.*x', 0)"})

    >>> to_string({"myfield": {"$regex": 'junk('}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid regular expression 'junk(': unbalanced parenthesis

    >>> to_string({"myfield": {"$regex": 'a', 'junk': 'junk'}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part "'junk'". You can only have `$options` with `$regex`.

    >>> to_string({"bubu": {"$regex": ".*", "$options": "junk"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'junk'. Unsupported regex option 'j'. Only 's', 'x', 'm', 'i' are supported !

    >>> to_string({"bubu": {"$options": "i"}})
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {'$options': 'i'}. Cannot have $options without $regex.

to_func
=======

::

    >>> from mongoql_conv import to_func

    >>> to_func({"myfield": 1}).source
    "lambda item: (item['myfield'] == 1) # compiled from {'myfield': 1}"

    >>> to_func({}).source
    'lambda item: (True) # compiled from {}'

    >>> list(filter(to_func({"myfield": 1}), [{"myfield": 1}, {"myfield": 2}]))
    [{'myfield': 1}]

    >>> list(filter(to_func({}), [{"myfield": 1}, {"myfield": 2}]))
    [{'myfield': 1}, {'myfield': 2}]

    >>> to_func({"myfield": {"$in": [1, 2]}}).source
    "lambda item, var0={1, 2}: (item['myfield'] in var0) # compiled from {'myfield': {'$in': [1, 2]}}"

    >>> list(filter(to_func({"myfield": {"$in": [1, 2]}}), [{"myfield": 1}, {"myfield": 2}]))
    [{'myfield': 1}, {'myfield': 2}]

    >>> to_func({"myfield": {"$in": {1: 2}}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

    >>> to_func({"myfield": {"$and": []}}).source
    "lambda item: (True) # compiled from {'myfield': {'$and': []}}"

    >>> list(filter(to_func({"myfield": {"$and": []}}), [{"myfield": 1}, {"myfield": 2}]))
    [{'myfield': 1}, {'myfield': 2}]


Supported operators
-------------------

Arithmetic
``````````

* **$gt**::

    >>> to_func({"myfield": {"$gt": 1}}).source
    "lambda item: (item['myfield'] > 1) # compiled from {'myfield': {'$gt': 1}}"
    >>> to_func({"myfield": {"$gt": [1]}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part [1]. Expected value of type int, float, str, unicode, bool or None.

    >>> list(filter(to_func({"myfield": {"$gt": 1}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 2}, {'myfield': 3}, {'myfield': 4}]


* **$gte**::

    >>> to_func({"myfield": {"$gte": 1}}).source
    "lambda item: (item['myfield'] >= 1) # compiled from {'myfield': {'$gte': 1}}"

    >>> list(filter(to_func({"myfield": {"$gte": 2}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 2}, {'myfield': 3}, {'myfield': 4}]

* **$lt**::

    >>> to_func({"myfield": {"$lt": 1}}).source
    "lambda item: (item['myfield'] < 1) # compiled from {'myfield': {'$lt': 1}}"

    >>> list(filter(to_func({"myfield": {"$lt": 1}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 0}]

* **$lte**::

    >>> to_func({"myfield": {"$lte": 1}}).source
    "lambda item: (item['myfield'] <= 1) # compiled from {'myfield': {'$lte': 1}}"

    >>> list(filter(to_func({"myfield": {"$lte": 1}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 0}, {'myfield': 1}]

* **$eq**::

    >>> to_func({"myfield": {"$eq": 1}}).source
    "lambda item: (item['myfield'] == 1) # compiled from {'myfield': {'$eq': 1}}"
    >>> to_func({"myfield": 1}).source
    "lambda item: (item['myfield'] == 1) # compiled from {'myfield': 1}"

    >>> list(filter(to_func({"myfield": {"$eq": 2}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 2}]

* **$ne**::

    >>> to_func({"myfield": {"$ne": 1}}).source
    "lambda item: (item['myfield'] != 1) # compiled from {'myfield': {'$ne': 1}}"

    >>> list(filter(to_func({"myfield": {"$ne": 2}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 0}, {'myfield': 1}, {'myfield': 3}, {'myfield': 4}]

* **$mod**::

    >>> to_func({"myfield": {"$mod": [2, 1]}}).source
    "lambda item: (item['myfield'] % 2 == 1) # compiled from {'myfield': {'$mod': [2, 1]}}"
    >>> to_func({"myfield": {"$mod": [2, 1, 3]}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part [2, 1, 3]. You must have two items: divisor and remainder.

    >>> to_func({"myfield": {"$mod": 2}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 2. Expected one of: list, tuple.

    >>> to_func({"myfield": {"$mod": (2, 1)}}).source
    "lambda item: (item['myfield'] % 2 == 1) # compiled from {'myfield': {'$mod': (2, 1)}}"

    >>> list(filter(to_func({"myfield": {"$mod": (2, 1)}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 1}, {'myfield': 3}]

Containers
``````````

* **$in**::

    >>> to_func({"myfield": {"$in": (1, 2, 3)}}).source
    "lambda item, var0={1, 2, 3}: (item['myfield'] in var0) # compiled from {'myfield': {'$in': (1, 2, 3)}}"

    >>> list(filter(to_func({"myfield": {"$in": (1, 2, 3)}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 1}, {'myfield': 2}, {'myfield': 3}]

* **$nin**::

    >>> to_func({"myfield": {"$nin": [1, 2, 3]}}).source
    "lambda item, var0={1, 2, 3}: (item['myfield'] not in var0) # compiled from {'myfield': {'$nin': [1, 2, 3]}}"

    >>> to_func({"myfield": {"$nin": {1: 2}}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

    >>> list(filter(to_func({"myfield": {"$nin": (1, 2, 3)}}), [{"myfield": i} for i in range(5)]))
    [{'myfield': 0}, {'myfield': 4}]

* **$size**::

    >>> to_func({"myfield": {"$size": 3}}).source
    "lambda item: (len(item['myfield']) == 3) # compiled from {'myfield': {'$size': 3}}"

    >>> to_func({"myfield": {"$size": "3"}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part '3'. Expected one of: int, long.

    >>> list(filter(to_func({"myfield": {"$size": 3}}), [{"myfield": 'x'*i} for i in range(5)]))
    [{'myfield': 'xxx'}]

    >>> list(filter(to_func({"myfield": {"$size": 3}}), [{"myfield": list(range(i))} for i in range(5)]))
    [{'myfield': [0, 1, 2]}]

* **$all**::

    >>> to_func({"myfield": {"$all": [1, 2, 3]}}).source
    "lambda item, var0={1, 2, 3}: (set(item['myfield']) >= var0) # compiled from {'myfield': {'$all': [1, 2, 3]}}"

    >>> to_func({"myfield": {"$all": 1}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 1. Expected one of: set, list, tuple, frozenset.

    >>> list(filter(to_func({"myfield": {"$all": [3, 4]}}), [{"myfield": list(range(i))} for i in range(7)]))
    [{'myfield': [0, 1, 2, 3, 4]}, {'myfield': [0, 1, 2, 3, 4, 5]}]

* **$exists**::

    >>> to_func({"myfield": {"$exists": True}}).source
    "lambda item: ('myfield' in item) # compiled from {'myfield': {'$exists': True}}"

    >>> to_func({"myfield": {"$exists": False}}).source
    "lambda item: ('myfield' not in item) # compiled from {'myfield': {'$exists': False}}"

    >>> list(filter(to_func({"$or": [{"field1": {"$exists": True}}, {"field2": {"$exists": False}}]}), [{"field%s" % i: i} for i in range(5)]))
    [{'field0': 0}, {'field1': 1}, {'field3': 3}, {'field4': 4}]

Boolean operators
`````````````````

* **$or**::

    >>> to_func({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}).source
    "lambda item: ((item['bubu'] > 1) or (item['bubu'] < 2)) # compiled from {'$or': [{'bubu': {'$gt': 1}}, {'bubu': {'$lt': 2}}]}"

    >>> to_func({'$or': "invalid value"}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.

    >>> list(filter(to_func({'$or': [{"bubu": {"$gt": 3}}, {'bubu': {'$lt': 2}}]}), [{"bubu": i} for i in range(5)]))
    [{'bubu': 0}, {'bubu': 1}, {'bubu': 4}]

* **$and**::

    >>> to_func({'$and': [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}).source
    "lambda item: ((item['bubu'] > 1) and (item['bubu'] < 2)) # compiled from {'$and': [{'bubu': {'$gt': 1}}, {'bubu': {'$lt': 2}}]}"
    >>> to_func({'$or': "invalid value"}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'invalid value'. Expected one of: list, tuple.
    >>> list(filter(to_func({'$and': [{"bubu": {"$lt": 3}}, {'bubu': {'$gt': 1}}]}), [{"bubu": i} for i in range(5)]))
    [{'bubu': 2}]

* **$*nesting***::

    >>> to_func({'$and': [
    ...     {"bubu": {"$gt": 1}},
    ...     {'$or': [
    ...         {'bubu': {'$lt': 2}},
    ...         {'$and': [
    ...             {'bubu': {'$lt': 3}},
    ...             {'bubu': {'$lt': 4}},
    ...         ]}
    ...     ]}
    ... ]}).source
    "lambda item: ((item['bubu'] > 1) and ((item['bubu'] < 2) or ((item['bubu'] < 3) and (item['bubu'] < 4)))) # compiled from {'$and': [{'bubu': {'$gt': 1}}, {'$or': [{'bubu': {'$lt': 2}}, {'$and': [{'bubu': {'$lt': 3}}, {'bubu': {'$lt': 4}}]}]}]}"

Regular expressions
```````````````````

* **$regex**::

    >>> to_func({"myfield": {"$regex": 'a'}}).source
    "lambda item, var0=re.compile('a', 0): (var0.match(item['myfield'])) # compiled from {'myfield': {'$regex': 'a'}}"

    >>> to_func({"myfield": {"$regex": 'a', "$options": 'i'}}).source
    "lambda item, var0=re.compile('a', 2): (var0.match(item['myfield'])) # compiled from {'myfield': {'$options': 'i', '$regex': 'a'}}"

    >>> to_func({"myfield": {"$regex": 'junk('}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid regular expression 'junk(': unbalanced parenthesis

    >>> to_func({"myfield": {"$regex": 'a', 'junk': 'junk'}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part "'junk'". You can only have `$options` with `$regex`.

    >>> to_func({"bubu": {"$regex": ".*", "$options": "junk"}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'junk'. Unsupported regex option 'j'. Only 's', 'x', 'm', 'i' are supported !

    >>> to_func({"bubu": {"$options": "i"}}).source
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {'$options': 'i'}. Cannot have $options without $regex.

    >>> import string
    >>> list(filter(to_func({"myfield": {"$regex": '[a-c]', "$options": 'i'}}), [{"myfield": i} for i in string.ascii_letters]))
    [{'myfield': 'a'}, {'myfield': 'b'}, {'myfield': 'c'}, {'myfield': 'A'}, {'myfield': 'B'}, {'myfield': 'C'}]


to_Q
====

Compiles down to a Django Q object tree::

    >>> from mongoql_conv.django import to_Q
    >>> print(to_Q({"myfield": 1}))
    (AND: ('myfield', 1))

    >>> print(to_Q({}))
    (AND: )

    >>> from test_app.models import MyModel
    >>> MyModel.objects.clean_and_create([(i, i) for i in range(5)])
    >>> MyModel.objects.filter(to_Q({"field1": 1}))
    [<MyModel: field1=1, field2='1'>]

    >>> print(to_Q({"field1": 1, "field2": 2}))
    (AND: ('field2', 2), ('field1', 1))

    >>> MyModel.objects.filter(to_Q({"field1": 1, "field2": 1}))
    [<MyModel: field1=1, field2='1'>]

    >>> print(to_Q({"myfield": {"$in": [1, 2]}}))
    (AND: ('myfield__in', [1, 2]))

    >>> MyModel.objects.filter(to_Q({"field1": {"$in": [1, 2]}}))
    [<MyModel: field1=1, field2='1'>, <MyModel: field1=2, field2='2'>]

    >>> print(to_Q({"myfield": {"$in": {1: 2}}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {1: 2}. Expected one of: set, list, tuple, frozenset.

    >>> print(to_Q({"myfield": {"$and": []}}))
    (AND: )

    >>> MyModel.objects.filter(to_Q({"field1": {"$and": []}}))
    [<MyModel: field1=0, field2='0'>, <MyModel: field1=1, field2='1'>, <MyModel: field1=2, field2='2'>, <MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]


Supported operators
-------------------

Arithmetic
``````````

* **$gt**::

    >>> print(to_Q({"myfield": {"$gt": 1}}))
    (AND: ('myfield__gt', 1))

    >>> MyModel.objects.filter(to_Q({"field1": {"$gt": 2}}))
    [<MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]

* **$gte**::

    >>> print(to_Q({"myfield": {"$gte": 1}}))
    (AND: ('myfield__gte', 1))

    >>> MyModel.objects.filter(to_Q({"field1": {"$gte": 2}}))
    [<MyModel: field1=2, field2='2'>, <MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]

* **$lt**::

    >>> print(to_Q({"myfield": {"$lt": 1}}))
    (AND: ('myfield__lt', 1))

    >>> MyModel.objects.filter(to_Q({"field1": {"$lt": 1}}))
    [<MyModel: field1=0, field2='0'>]

* **$lte**::

    >>> print(to_Q({"myfield": {"$lte": 1}}))
    (AND: ('myfield__lte', 1))

    >>> MyModel.objects.filter(to_Q({"field1": {"$lte": 1}}))
    [<MyModel: field1=0, field2='0'>, <MyModel: field1=1, field2='1'>]

* **$eq**::

    >>> print(to_Q({"myfield": {"$eq": 1}}))
    (AND: ('myfield', 1))

    >>> MyModel.objects.filter(to_Q({"field1": 1}))
    [<MyModel: field1=1, field2='1'>]

    >>> print(to_Q({"myfield": 1}))
    (AND: ('myfield', 1))

    >>> MyModel.objects.filter(to_Q({"field1": {"$eq": 1}}))
    [<MyModel: field1=1, field2='1'>]

* **$ne**::

    >>> print(to_Q({"myfield": {"$ne": 1}}))
    (NOT (AND: ('myfield', 1)))

    >>> MyModel.objects.filter(to_Q({"field1": {"$ne": 1}}))
    [<MyModel: field1=0, field2='0'>, <MyModel: field1=2, field2='2'>, <MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]

* **$mod**::

    >>> print(to_Q({"myfield": {"$mod": [2, 1]}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: DjangoVisitor doesn't support operator '$mod'


Containers
``````````

* **$in**::

    >>> print(to_Q({"myfield": {"$in": (1, 2, 3)}}))
    (AND: ('myfield__in', (1, 2, 3)))

    >>> MyModel.objects.filter(to_Q({"field1": {"$in": (1, 2)}}))
    [<MyModel: field1=1, field2='1'>, <MyModel: field1=2, field2='2'>]

* **$nin**::

    >>> print(to_Q({"myfield": {"$nin": [1, 2, 3]}}))
    (NOT (AND: ('myfield__in', [1, 2, 3])))

    >>> MyModel.objects.filter(to_Q({"field1": {"$nin": (1, 2)}}))
    [<MyModel: field1=0, field2='0'>, <MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]

* **$size**::

    >>> print(to_Q({"myfield": {"$size": 3}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: DjangoVisitor doesn't support operator '$size'

* **$all**::

    >>> print(to_Q({"myfield": {"$all": [1, 2, 3]}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: DjangoVisitor doesn't support operator '$all'

* **$exists**::

    >>> print(to_Q({"myfield": {"$exists": True}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: DjangoVisitor doesn't support operator '$exists'

Boolean operators
`````````````````

* **$or**::

    >>> print(to_Q({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}))
    (OR: ('bubu__gt', 1), ('bubu__lt', 2))

    >>> MyModel.objects.filter(to_Q({'$or': [{"field1": {"$gt": 3}}, {'field1': {'$lt': 2}}]}))
    [<MyModel: field1=0, field2='0'>, <MyModel: field1=1, field2='1'>, <MyModel: field1=4, field2='4'>]

* **$and**::

    >>> print(to_Q({'$and':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}))
    (AND: ('bubu__gt', 1), ('bubu__lt', 2))

    >>> MyModel.objects.filter(to_Q({'$and': [{"field1": {"$gt": 1}}, {'field1': {'$lt': 3}}]}))
    [<MyModel: field1=2, field2='2'>]

* **$*nesting***::

    >>> print(to_Q({'$and': [
    ...     {"bubu": {"$gt": 1}},
    ...     {'$or': [
    ...         {'bubu': {'$lt': 2}},
    ...         {'$and': [
    ...             {'bubu': {'$lt': 3}},
    ...             {'bubu': {'$lt': 4}},
    ...         ]}
    ...     ]}
    ... ]}))
    (AND: ('bubu__gt', 1), (OR: ('bubu__lt', 2), (AND: ('bubu__lt', 3), ('bubu__lt', 4))))

    >>> MyModel.objects.filter(to_Q({'$and': [
    ...     {"field1": {"$gt": 1}},
    ...     {'$or': [
    ...         {'field2': {'$lt': 2}},
    ...         {'$and': [
    ...             {'field2': {'$lt': 5}},
    ...             {'field2': {'$gt': 2}},
    ...         ]}
    ...     ]}
    ... ]}))
    [<MyModel: field1=3, field2='3'>, <MyModel: field1=4, field2='4'>]

Regular expressions
```````````````````

* **$regex**::

    >>> print(to_Q({"myfield": {"$regex": 'a'}}))
    (AND: ('myfield__regex', 'a'))

    >>> print(to_Q({"myfield": {"$regex": 'a', "$options": 'i'}}))
    (AND: ('myfield__iregex', 'a'))

    >>> print(to_Q({"myfield": {"$regex": 'junk('}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid regular expression 'junk(': unbalanced parenthesis

    >>> print(to_Q({"myfield": {"$regex": 'a', 'junk': 'junk'}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part "'junk'". You can only have `$options` with `$regex`.

    >>> print(to_Q({"bubu": {"$regex": ".*", "$options": "mxs"}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part 'mxs'. Unsupported regex option 'm'. Only i are supported !

    >>> print(to_Q({"bubu": {"$options": "i"}}))
    Traceback (most recent call last):
    ...
    InvalidQuery: Invalid query part {'$options': 'i'}. Cannot have $options without $regex.

    >>> MyModel.objects.clean_and_create([(None, i) for i in string.ascii_letters])
    >>> MyModel.objects.filter(to_Q({"field2": {"$regex": '[a-b]', "$options": 'i'}}))
    [<MyModel: field1=None, field2='a'>, <MyModel: field1=None, field2='b'>, <MyModel: field1=None, field2='A'>, <MyModel: field1=None, field2='B'>]


Extending (implementing a custom visitor)
=========================================

There are few requirements for a visitor. Fist, you need to be able to render boolean $and::

    >>> from mongoql_conv import BaseVisitor
    >>> class MyVisitor(BaseVisitor):
    ...     def __init__(self, object_name):
    ...         self.object_name = object_name
    ...     def visit_foobar(self, value, field_name, context):
    ...         return "foobar(%s[%r], %r)" % (self.object_name, field_name, value)
    >>> MyVisitor('obj').visit({'field': {'$foobar': 'test'}})
    Traceback (most recent call last):
    ...
    TypeError: Can't instantiate abstract class MyVisitor with abstract methods render_and

This is the minimal code to have a custom generator::

    >>> class MyVisitor(BaseVisitor):
    ...     def __init__(self, object_name):
    ...         self.object_name = object_name
    ...     def visit_foobar(self, value, field_name, context):
    ...         return "foobar(%s[%r], %r)" % (self.object_name, field_name, value)
    ...     def render_and(self, parts, field_name, context):
    ...         return ' & '.join(parts)
    >>> MyVisitor('obj').visit({'field': {'$foobar': 'test'}})
    "foobar(obj['field'], 'test')"

Ofcourse, it won't do much::

    >>> MyVisitor('obj').visit({'field': {'$ne': 'test'}})
    Traceback (most recent call last):
    ...
    InvalidQuery: MyVisitor doesn't support operator '$ne'

Take a look at ``ExprVisitor`` too see all the methods you *should* implement.
