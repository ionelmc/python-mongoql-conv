"""
Converts a dict containing a mongo query to a lambda. Doesn't support all the mongo
query $keywords, probably differs the result in subtle ways.

It only supports querying flat structures: dicts with no lists or other dicts in
them (aka subdocuments).
"""
from __future__ import print_function

import linecache
import re
import sys
import tempfile
import weakref
import zlib
from abc import ABCMeta
from abc import abstractmethod
from collections import Iterable, Sized
from functools import wraps
from types import NoneType
from six import with_metaclass

class InvalidQuery(Exception):
    pass

if sys.version_info[0] == 3:
    unicode = str

def ensure_type(*types):
    def ensure_type_(self, value, *args):
        if not isinstance(value, types):
            raise InvalidQuery('Invalid query part %r. Expected one of: %s.' % (
                value,
                ', '.join('None' if t is NoneType else t.__name__ for t in types)
            ))
    return ensure_type_

def validated_method(validator_name, func):
    def validated_method_wrapper(self, *args, **kwargs):
        if hasattr(self, validator_name):
            getattr(self, validator_name)(*args, **kwargs)
        else:
            raise RuntimeError("Missing validator %s in %s" % (validator_name, type(self).__name__))
        return func(self, *args, **kwargs)
    return validated_method_wrapper

def validator_metaclass(base=type):
    return type(
        base.__name__ + "WithValidatorMeta",
        (base, ),
        {'__new__': lambda mcls, name, bases, namespace: file('x', 'w').write(`namespace`) or base.__new__(mcls, name, bases, {
            name: validated_method('validate_'+name[6:], func)
                  if callable(func) and name.startswith('visit_')
                  else func
            for name, func in namespace.items()
        })}
    )

def require(*types):
    def require_(value, *args, **kwargs):
        if not isinstance(value, types):
            raise InvalidQuery('Invalid query part %r. Expected one of: %s.' % (
                value,
                ', '.join('None' if t is NoneType else t.__name__ for t in types)
            ))
    return require_

def require_value(value, *args, **kwargs):
    if not isinstance(value, (int, float, str, unicode, bool, NoneType)):
        raise InvalidQuery(
            'Invalid query part %r. Expected value of type int, float, str, unicode, bool or None.' % value
        )

def require_iterable(value, *args, **kwargs):
    if not isinstance(value, (Sized, Iterable)):
        raise InvalidQuery('Invalid query part %r. Expected an iterable value with a size.' % value)

class BaseVisitor(with_metaclass(validator_metaclass(base=ABCMeta))):
    def __init__(self, closure, object_name):
        self.closure = closure
        self.object_name = object_name


    validate_gt = validate_gte = validate_lt = validate_lte = validate_ne = validate_eq = staticmethod(require_value)
    validate_item = staticmethod(require(tuple))
    validate_query = lambda *args, **kwargs: None
    validate_and = validate_or = staticmethod(require(list, tuple))
    validate_in = validate_nin = staticmethod(require(set, list, tuple, frozenset))
    #def validate_and(self, value, field_name):
    #                if field_name is not None:
    #                    raise InvalidQuery("Can't query part %r for field %r." % (value, field_name))

    @abstractmethod
    def visit_eq(self, value, field_name):
        pass

    @abstractmethod
    def visit_and(self, parts):
        multiple = len(parts) > 1
        return ' and '.join('(%s)' % part if multiple else part for part in parts)

    def visit(self, query):
        return self.visit_query(query, None)

    def visit_query(self, query, field_name):
        parts = [self.handle_item(item, field_name) for item in query.items()]
        return self.render_and(parts, field_name)

    def handle_item(self, item, field_name):
        name, value = item
        if name.startswith('$'):
            opname = name[1:]
            handler = 'visit_' + opname
            if hasattr(self, handler):
                handler = getattr(self, handler)
                return handler(value, field_name)
            else:
                raise InvalidQuery("%s doesn't support operator %r" % (type(self).__name__, name))
        elif isinstance(value, dict):
            return self.visit_query(value, name)
        else:
            return self.visit_eq(value, name)

    def visit_and(self, parts, field_name=None, operator=' and '):
        multiple = len(parts) > 1
        return ' and '.join(self.visit_query(part, field_name) for part in parts)

class ExprVisitor(BaseVisitor):
    def visit_gt(self, value, field_name):
        return "%s[%r] > %r" % (self.object_name, field_name, value)

    def visit_gte(self, value, field_name):
        return "%s[%r] >= %r" % (self.object_name, field_name, value)

    def visit_lt(self, value, field_name):
        return "%s[%r] < %r" % (self.object_name, field_name, value)

    def visit_lte(self, value, field_name):
        return "%s[%r] <= %r" % (self.object_name, field_name, value)

    def visit_ne(self, value, field_name):
        return "%s[%r] != %r" % (self.object_name, field_name, value)

    def visit_eq(self, value, field_name):
        return "%s[%r] == %r" % (self.object_name, field_name, value)

    def visit_in(self, value, field_name, operator='in'):
        if self.closure is None:
            var_name = "{%s}" % ", ".join(repr(i) for i in value)
        else:
            var_name = "var%s" % len(self.closure)
            arguments[var_name] = "{%s}" % ", ".join(repr(i) for i in value)
        return "%s[%r] %s %s" % (self.object_name, field_name, operator, var_name)

    def visit_nin(self, value, field_name):
        return self.visit_in(value, field_name, 'not in')

    def visit_and(self, parts, field_name=None, operator=' and '):
        return self.render_and([self.visit_query(part, field_name) for part in parts], field_name, operator)

    def visit_or(self, parts, field_name=None):
        return self.visit_and(parts, operator=' or ')

    def render_and(self, parts, field_name=None, operator=' and '):
        multiple = len(parts) > 1
        return operator.join("(%s)" % part if multiple else part for part in parts)

def compile_to_string(
    query,
    arguments=None,
    field_name=None,
    object_name='row',
    operators={
        'gt': ">",
        'gte': ">=",
        'lt': "<",
        'lte': "<=",
        'ne': "!=",
        'eq': "==",
    }, container_operators={
        'in': "in",
        'nin': "not in",
        'all': "",
        'size': ""
    }, expression_operators={
        'regex': "re.match(%r, %s[%r], %r)",
        'mod': '',
        'type': '',
        'exists': '',
    }
):
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
                if arguments is None:
                    var_name = "{%s}" % ", ".join(repr(i) for i in value)
                else:
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

def compile_to_string(query, closure=None, object_name='row'):
    visitor = ExprVisitor(closure, object_name)
    return visitor.visit(query)

def compile_to_func(query, use_arguments=True):
    arguments = {} if use_arguments else None
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
    import sys
    import cgitb
    cgitb.enable(format='text')
    print(compile_to_string({'$and':  [{"bubu": 1}, {'bubu': 2}]}))
    print(compile_to_string({'$or':  [{"bubu": 1}, {'bubu': 2}]}))
    print(compile_to_string({"myfield": {"$in": [1, 2]}}))

    sys.exit()
    import timeit
    print(timeit.timeit(
        "for i in data:\n"
        "  func(i)",
        "from __main__ import *\n"
        "func = compile_to_func({'f': {'$in': range(10)}})\n"
        "data = [{'f': i%20} for i in range(100)]",
        number=1000000
    ))
    print(timeit.timeit(
        "for i in data:\n"
        "  func(i)",
        "from __main__ import *\n"
        "func = compile_to_func({'f': {'$in': range(10)}}, use_arguments=False)\n"
        "data = [{'f': i%20} for i in range(100)]",
        number=1000000
    ))


    sys.exit()
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
