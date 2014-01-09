"""
Converts a dict containing a mongo query to a lambda. Doesn't support all the mongo
query $keywords, probably differs the result in subtle ways.

It only supports querying flat structures: dicts with no lists or other dicts in
them (aka subdocuments).
"""
from __future__ import print_function
import sys
import tempfile
import zlib
import linecache
import weakref

class InvalidQuery(Exception):
    pass

if sys.version_info[0] == 3:
    unicode = str

def compile_to_string(query, arguments, field_name=None, object_name='row', operators={
    'gt': ">", 'gte': ">=", 'lt': "<", 'lte': "<=", 'ne': "!=", 'eq': "==",
}, container_operators={
    'in': "in", 'nin': "not in"
}):
    parts = []
    for name, value in query.items():
        if name.startswith('$'):
            opname = name[1:]
            if opname in ('and', 'or'):
                if field_name is not None:
                    raise InvalidQuery("Can't query part %r for field %r." % (value, field_name))
                if not isinstance(value, list):
                    raise InvalidQuery('Invalid query part %r. Expected a list.' % value)
                parts.append((' %s ' % opname).join('(%s)' % compile_to_string(item, arguments, object_name=object_name) for item in value))
            elif opname in operators:
                if not isinstance(value, (int, float, str, unicode, bool)):
                    raise InvalidQuery('Invalid query part %r. Expected one of: int, float, string, bool.' % value)
                parts.append("%s[%r] %s %r" % (object_name, field_name, operators[opname], value))
            elif opname in container_operators:
                if not isinstance(value, (set, list, tuple, frozenset)):
                    raise InvalidQuery('Invalid query part %r. Expected a list, tuple or set.' % value)
                var_name = "var%s" % len(arguments)
                arguments[var_name] = "{%s}" % ", ".join(repr(i) for i in value)
                parts.append("%s[%r] %s %s" % (object_name, field_name, container_operators[opname], var_name))
            elif opname == 'not':
                parts.append("not (%s)" % compile_to_string(value, arguments, field_name=field_name, object_name=object_name))
            else:
                raise InvalidQuery('Invalid operator %r' % name)
        elif isinstance(value, dict):
            parts.append(compile_to_string(value, arguments, field_name=name, object_name=object_name))
        else:
            parts.append(compile_to_string({'$eq': value}, arguments, field_name=name, object_name=object_name))
    multiple = len(parts) > 1
    return ' and '.join('(%s)' % part if multiple else part for part in parts)

def compile_to_func(query):
    arguments = {}
    as_string = compile_to_string(query, arguments, object_name='item')
    as_code = "lambda item%s: (%s) # compiled from %r" % (
        ', ' + ', '.join('%s=%s' % (var_name, value) for var_name, value in arguments.items()) if arguments else '',
        as_string,
        query
    )
    filename = "<query-function-%x>" % zlib.adler32(as_string.encode('utf8'))
    func = eval(compile(as_code, filename, 'eval'))
    linecache.cache[filename] = len(as_code), None, [as_code], filename
    func.query = query
    func.source = as_code
    func.cleanup = weakref.ref(func, lambda _, filename=filename: linecache.cache.pop(filename, None))
    return func

if __name__ == '__main__':
    print(compile_to_func({"bubu": {"$gt": 1, '$lt': 2}}).source)
    print(compile_to_func({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}).source)
    print(compile_to_func({"bubu": {"$gt": 1, '$lt': 2}}).source)
    print(compile_to_func({"lulu": {"$in": [1, 2]}}).source)
    print(compile_to_func({'$or':  [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}).source)
    print(compile_to_func({'$and': [{"bubu": {"$gt": 1}}, {'bubu': {'$lt': 2}}]}).source)
    print(compile_to_func({'$and': [
        {"bubu": {"$gt": 1}},
        {'$or': [
            {'bubu': {'$lt': 2}},
            {'$and': [
                {'bubu': {'$lt': 3}},
                {'bubu': {'$lt': 4}},
            ]}
        ]}
    ]}).source)
    print(compile_to_func({"bubu": {"$ne": 1, '$nin': [2, 3]}}).source)
    print(compile_to_func({"bubu": {'$not': {"$ne": 1, '$in': [2, 3]}}}).source)
    print(compile_to_func({"bubu": {"$ne": 1}}).source)