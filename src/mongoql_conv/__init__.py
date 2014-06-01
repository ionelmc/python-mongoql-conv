"""
Converts a dict containing a mongo query to a lambda. Doesn't support all the mongo
query $keywords, probably differs the result in subtle ways.

It only supports querying flat structures: dicts with no lists or other dicts in
them (aka subdocuments).
"""
from __future__ import absolute_import
from __future__ import print_function

import linecache
import re
import sys
import weakref
import zlib
from abc import ABCMeta
from abc import abstractmethod
from warnings import warn

from six import reraise
from six import with_metaclass

__all__ = "InvalidQuery", "to_string", "to_func"

NoneType = type(None)


class InvalidQuery(Exception):
    pass  # pragma: no cover


def validated_method(validator_name, func):
    def validated_method_wrapper(self, value, *args, **kwargs):
        if hasattr(self, validator_name):
            value = getattr(self, validator_name)(value, *args, **kwargs)
        else:
            warn("Missing validator %s in %s" % (validator_name, type(self).__name__))
        return func(self, value, *args, **kwargs)
    return validated_method_wrapper


def validator_metaclass(base=type):
    return type(
        base.__name__ + "WithValidatorMeta",
        (base, ),
        {'__new__': lambda mcls, name, bases, namespace: base.__new__(mcls, name, bases, {
            name: (
                validated_method('validate_'+name[6:], func)
                if callable(func) and name.startswith('visit_')
                else func
            )
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
        return value
    return require_

if sys.version_info[0] == 3:
    require_string = require(str)
    require_integer = require(int)
    require_value = require(int, float, str, bool, NoneType)
else:
    require_string = require(str, unicode)
    require_integer = require(int, long)
    require_value = require(int, long, float, str, unicode, bool, NoneType)

Skip = object()
Stripped = object()
Missing = object()


class BaseVisitor(with_metaclass(validator_metaclass(base=ABCMeta))):
    validate_gt = validate_gte = validate_lt = validate_lte = validate_ne = validate_eq = staticmethod(require_value)
    validate_query = staticmethod(require(dict))
    validate_exists = staticmethod(require(object))
    validate_and = validate_or = staticmethod(require(list, tuple))
    validate_all = validate_in = validate_nin = staticmethod(require(set, list, tuple, frozenset))
    validate_size = staticmethod(require_integer)

    def validate_mod(self, value, field_name, context):
        self.validate_and(value)
        if len(value) != 2:
            raise InvalidQuery('Invalid query part %r. You must have two items: divisor and remainder.' % value)
        return value

    def validate_regex(self, value, field_name, context, acceptable_options=('s', 'x', 'm', 'i')):
        options = context.get('$options', Missing)
        regex = context.get('$regex', Missing)
        if Stripped in (options, regex):
            return Stripped

        extra_keys = set(i for i in context if not i.startswith('$'))
        if extra_keys:
            raise InvalidQuery('Invalid query part %r. You can only have `$options` with `$regex`.' % ', '.join(
                repr(k) for k in extra_keys
            ))

        if regex is Missing:
            raise InvalidQuery('Invalid query part %r. Cannot have $options without $regex.' % context)
        require_string(regex)
        raw_options = 0
        if options is not Missing:
            require_string(options)
            for opt in options:
                if opt not in acceptable_options:
                    raise InvalidQuery(
                        "Invalid query part %r. Unsupported regex option %r. Only %s are supported !" % (
                            options, opt, ', '.join(acceptable_options)
                        )
                    )
                raw_options |= getattr(re, opt.upper())
        try:
            re.compile(regex, raw_options)
        except re.error as exc:
            reraise(InvalidQuery, InvalidQuery("Invalid regular expression %r: %s" % (value, exc)), sys.exc_info()[2])
        context['$regex'] = Stripped
        if '$options' in context:
            context['$options'] = Stripped
        return regex, raw_options
    validate_options = validate_regex

    @abstractmethod
    def visit_eq(self, value, field_name, context):
        pass  # pragma: no cover

    @abstractmethod
    def render_and(self, parts):
        pass  # pragma: no cover

    def visit(self, query):
        return self.visit_query(query)

    def visit_query(self, query, field_name=None, context=None):
        return self.render_and([
            part
            for part in self.handle_query(query, field_name)
            if part is not Skip
        ], field_name, context)

    def handle_query(self, query, field_name, context=None):
        query = query.copy()
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
    def __init__(self, closure, object_name):
        self.closure = closure
        self.object_name = object_name

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
            self.closure[var_name] = "{%s}" % ", ".join(repr(i) for i in value)
        return "%s[%r] %s %s" % (self.object_name, field_name, operator, var_name)

    def visit_nin(self, value, field_name, context):
        return self.visit_in(value, field_name, context, 'not in')

    def visit_and(self, parts, field_name, context, operator=' and '):
        return self.render_and([self.visit_query(part, field_name) for part in parts], field_name, context, operator)

    def visit_or(self, parts, field_name, context):
        return self.visit_and(parts, field_name, context, ' or ')

    def render_and(self, parts, field_name, context, operator=' and '):
        multiple = len(parts) > 1
        return operator.join("(%s)" % part if multiple else part for part in parts) or 'True'

    def visit_regex(self, value, field_name, context):
        if value is Stripped:
            return Skip
        else:
            regex, options = value

            if self.closure is None:
                return "re.search(%r, %s[%r], %r)" % (regex, self.object_name, field_name, options)
            else:
                var_name = "var%s" % len(self.closure)
                self.closure[var_name] = "re.compile(%r, %r)" % (regex, options)
                return '%s.search(%s[%r])' % (var_name, self.object_name, field_name)
    visit_options = visit_regex

    def visit_size(self, value, field_name, context):
        return "len(%s[%r]) == %r" % (self.object_name, field_name, value)

    def visit_all(self, value, field_name, context):
        if self.closure is None:
            return 'set(%s[%r]) >= {%s}' % (self.object_name, field_name, ', '.join(repr(i) for i in value))
        else:
            var_name = "var%s" % len(self.closure)
            self.closure[var_name] = "{%s}" % ', '.join(repr(i) for i in value)
            return 'set(%s[%r]) >= %s' % (self.object_name, field_name, var_name)

    def visit_mod(self, value, field_name, context):
        divisor, remainder = value
        return '%s[%r] %% %s == %s' % (self.object_name, field_name, divisor, remainder)

    def visit_exists(self, value, field_name, context):
        return '%r %sin %s' % (
            field_name, '' if value else 'not ', self.object_name,
        )


class LaxNone(object):
    __str__ = __repr__ = staticmethod(lambda: "LaxNone")
    __eq__ = __lt__ = __le__ = __ne__ = __gt__ = __ge__ = staticmethod(lambda _: False)
    __len__ = staticmethod(lambda: 0)
    __iter__ = staticmethod(lambda: iter(()))
    __mod__ = staticmethod(lambda _: LaxNone)
    __hash__ = None
LaxNone = LaxNone()


class LaxExprVisitor(BaseVisitor):
    def __init__(self, closure, object_name):
        self.closure = closure
        self.object_name = object_name

    def visit_gt(self, value, field_name, context):
        return "%s.get(%r, LaxNone) > %r" % (self.object_name, field_name, value)

    def visit_gte(self, value, field_name, context):
        return "%s.get(%r, LaxNone) >= %r" % (self.object_name, field_name, value)

    def visit_lt(self, value, field_name, context):
        return "%s.get(%r, LaxNone) < %r" % (self.object_name, field_name, value)

    def visit_lte(self, value, field_name, context):
        return "%s.get(%r, LaxNone) <= %r" % (self.object_name, field_name, value)

    def visit_ne(self, value, field_name, context):
        return "%s.get(%r, LaxNone) != %r" % (self.object_name, field_name, value)

    def visit_eq(self, value, field_name, context):
        return "%s.get(%r, LaxNone) == %r" % (self.object_name, field_name, value)

    def visit_in(self, value, field_name, context, operator='in', juction='and'):
        if self.closure is None:
            var_name = "{%s}" % ", ".join(repr(i) for i in value)
        else:
            var_name = "var%s" % len(self.closure)
            self.closure[var_name] = "{%s}" % ", ".join(repr(i) for i in value)
        return "%r %s %s %s %s.get(%r, LaxNone) %s %s" % (
            field_name, operator, self.object_name, juction, self.object_name, field_name, operator, var_name
        )

    def visit_nin(self, value, field_name, context):
        return self.visit_in(value, field_name, context, 'not in', 'or')

    def visit_and(self, parts, field_name, context, operator=' and '):
        return self.render_and([self.visit_query(part, field_name) for part in parts], field_name, context, operator)

    def visit_or(self, parts, field_name, context):
        return self.visit_and(parts, field_name, context, ' or ')

    def render_and(self, parts, field_name, context, operator=' and '):
        multiple = len(parts) > 1
        return operator.join("(%s)" % part if multiple else part for part in parts) or 'True'

    def visit_regex(self, value, field_name, context):
        if value is Stripped:
            return Skip
        else:
            regex, options = value

            if self.closure is None:
                return "re.search(%r, %s.get(%r, ''), %r)" % (regex, self.object_name, field_name, options)
            else:
                var_name = "var%s" % len(self.closure)
                self.closure[var_name] = "re.compile(%r, %r)" % (regex, options)
                return "%s.search(%s.get(%r, ''))" % (var_name, self.object_name, field_name)
    visit_options = visit_regex

    def visit_size(self, value, field_name, context):
        return "len(%s.get(%r, LaxNone)) == %r" % (self.object_name, field_name, value)

    def visit_all(self, value, field_name, context):
        if self.closure is None:
            return 'set(%s.get(%r, LaxNone)) >= {%s}' % (self.object_name, field_name, ', '.join(repr(i) for i in value))
        else:
            var_name = "var%s" % len(self.closure)
            self.closure[var_name] = "{%s}" % ', '.join(repr(i) for i in value)
            return 'set(%s.get(%r, LaxNone)) >= %s' % (self.object_name, field_name, var_name)

    def visit_mod(self, value, field_name, context):
        divisor, remainder = value
        return '%s.get(%r, LaxNone) %% %s == %s' % (self.object_name, field_name, divisor, remainder)

    def visit_exists(self, value, field_name, context):
        return '%r %sin %s' % (
            field_name, '' if value else 'not ', self.object_name,
        )


def to_string(query, closure=None, object_name='row', lax=False):
    visitor = (LaxExprVisitor if lax else ExprVisitor)(closure, object_name)
    return visitor.visit(query)


def to_func(query, use_arguments=True, lax=False):
    closure = {} if use_arguments else None
    as_string = to_string(query, closure, object_name='item', lax=lax)
    as_code = "lambda item%s: (%s) # compiled from %r" % (
        ', ' + ', '.join('%s=%s' % (var_name, value) for var_name, value in closure.items()) if closure else '',
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
