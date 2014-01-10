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
from six import with_metaclass, reraise

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
    def validated_method_wrapper(self, value, *args, **kwargs):
        if hasattr(self, validator_name):
            getattr(self, validator_name)(value, *args, **kwargs)
        else:
            raise RuntimeError("Missing validator %s in %s" % (validator_name, type(self).__name__))
        return func(self, value, *args, **kwargs)
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
    if not isinstance(value, (int, long, float, str, unicode, bool, NoneType)):
        raise InvalidQuery(
            'Invalid query part %r. Expected value of type int, float, str, unicode, bool or None.' % value
        )

def require_iterable(value, *args, **kwargs):
    if not isinstance(value, (Sized, Iterable)):
        raise InvalidQuery('Invalid query part %r. Expected an iterable value with a size.' % value)

require_string = require(str, unicode)

Skip = object()

class BaseVisitor(with_metaclass(validator_metaclass(base=ABCMeta))):
    def __init__(self, closure, object_name):
        self.closure = closure
        self.object_name = object_name


    validate_gt = validate_gte = validate_lt = validate_lte = validate_ne = validate_eq = staticmethod(require_value)
    validate_item = staticmethod(require(tuple))
    validate_query = staticmethod(require(object))
    validate_and = validate_or = staticmethod(require(list, tuple))
    validate_all = validate_in = validate_nin = staticmethod(require(set, list, tuple, frozenset))
    validate_size = staticmethod(require(int, long))


    def validate_regex(self, value, field_name, context, stripped=object(), missing=object()):
        options = context.get('$options', missing)
        regex = context.get('$regex', missing)

        extra_keys = set(context) - {'$options', '$regex'}
        if extra_keys:
            raise InvalidQuery('Invalid query part %r. You can only have `$options` with `$regex`.' % ', '.join(
                repr(k) for k in extra_keys
            ))

        if regex is missing:
            raise InvalidQuery('Invalid query part %r. Cannot have $options without $regex.' % context)
        require_string(regex)
        raw_options = 0
        if options is not missing:
            require_string(options)
            for opt in options:
                if opt not in ('s', 'x', 'm', 'i'):
                    raise InvalidQuery(
                        "Invalid query part %r. Unsupported regex option %r. Only 's', 'x', 'm', 'i' are supported !" % (
                            value, opt
                        )
                    )
                raw_options |= getattr(re, opt.upper())
        try:
            re.compile(regex, raw_options)
        except re.error as exc:
            reraise(InvalidQuery, "Invalid regular expression %r: %s" % (value, exc), sys.exc_info()[2])

        context['$options'] = context['$regex'] = regex, raw_options
    validate_options = validate_regex

    @abstractmethod
    def visit_eq(self, value, field_name, context):
        pass

    @abstractmethod
    def visit_and(self, parts):
        multiple = len(parts) > 1
        return ' and '.join('(%s)' % part if multiple else part for part in parts)

    def visit(self, query):
        return self.visit_query(query)

    def visit_query(self, query, field_name=None, context=None):
        return self.render_and([
            part
            for part in self.handle_query(query, field_name)
            if part is not Skip
        ], field_name, context)

    def handle_query(self, query, field_name, context=None):
        for name, value in query.items():
            if name.startswith('$'):
                opname = name[1:]
                handler = 'visit_' + opname
                if hasattr(self, handler):
                    handler = getattr(self, handler)
                    yield handler(value, field_name, query)
                else:
                    raise InvalidQuery("%s doesn't support operator %r" % (type(self).__name__, name))
            elif isinstance(value, dict):
                yield self.visit_query(value, name, query)
            else:
                yield self.visit_eq(value, name, query)

class ExprVisitor(BaseVisitor):
    def visit_gt(self, value, field_name, context):
        return "%s[%r] > %r" % (self.object_name, field_name, value)

    def visit_gte(self, value, field_name, context):
        return "%s[%r] >= %r" % (self.object_name, field_name, value)

    def visit_lt(self, value, field_name, context):
        return "%s[%r] < %r" % (self.object_name, field_name, value)

    def visit_lte(self, value, field_name, context):
        return "%s[%r] <= %r" % (self.object_name, field_name, value)

    def visit_ne(self, value, field_name, context):
        return "%s[%r] != %r" % (self.object_name, field_name, value)

    def visit_eq(self, value, field_name, context):
        return "%s[%r] == %r" % (self.object_name, field_name, value)

    def visit_in(self, value, field_name, context, operator='in'):
        if self.closure is None:
            var_name = "{%s}" % ", ".join(repr(i) for i in value)
        else:
            var_name = "var%s" % len(self.closure)
            arguments[var_name] = "{%s}" % ", ".join(repr(i) for i in value)
        return "%s[%r] %s %s" % (self.object_name, field_name, operator, var_name)

    def visit_nin(self, value, field_name, context):
        return self.visit_in(value, field_name, context, 'not in')

    def visit_and(self, parts, field_name, context, operator=' and '):
        return self.render_and([self.visit_query(part, field_name) for part in parts], field_name, context, operator)

    def visit_or(self, parts, field_name, context):
        return self.visit_and(parts, field_name, context, operator=' or ')

    def render_and(self, parts, field_name, context, operator=' and '):
        multiple = len(parts) > 1
        return operator.join("(%s)" % part if multiple else part for part in parts)

    def visit_regex(self, value, field_name, context):
        value = context.get('$options', context.get('$regex'))
        if value:
            regex, options = value

            if self.closure is None:
                return "re.match(%r, %s[%r], %r)" % (regex, self.object_name, field_name, options)
            else:
                var_name = "var%s" % len(self.closure)
                self.closure[var_name] = "re.compile(%r, %r)" % (regex, options)
                return '%s.match(%s[%r]' % (var_name, self.object_name, field_name)
        else:
            return Skip
    visit_options = visit_regex

    def visit_size(self, value, field_name, context):
        return "len(%s[%r]) == %r" % (self.object_name, field_name, value)

    def visit_all(self, value, field_name, context):
        if self.closure:
            var_name = "var%s" % len(self.closure)
            self.closure[var_name] = "{%s}" % ', '.join(repr(i) for i in value)
            return 'set(%s[%r]) == %s' % (self.object_name, field_name, var_name)
        else:
            return 'set(%s[%r]) == {%s}' % (self.object_name, field_name, ', '.join(repr(i) for i in value))

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
