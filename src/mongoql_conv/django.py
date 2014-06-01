from __future__ import absolute_import

from functools import partial
from operator import iand
from operator import ior
from functools import reduce
from re import IGNORECASE

from django.db.models import Q

from mongoql_conv import BaseVisitor, Stripped, Skip


class DjangoVisitor(BaseVisitor):
    def visit_gt(self, value, field_name, context):
        return Q(("%s__gt" % field_name, value))

    def visit_gte(self, value, field_name, context):
        return Q(("%s__gte" % field_name, value))

    def visit_lt(self, value, field_name, context):
        return Q(("%s__lt" % field_name, value))

    def visit_lte(self, value, field_name, context):
        return Q(("%s__lte" % field_name, value))

    def visit_ne(self, value, field_name, context):
        return ~self.visit_eq(value, field_name, context)

    def visit_eq(self, value, field_name, context):
        return Q((field_name, value))

    def visit_in(self, value, field_name, context, operator='in'):
        return Q(("%s__in" % field_name, value))

    def visit_nin(self, value, field_name, context):
        return ~self.visit_in(value, field_name, context)

    def visit_and(self, parts, field_name, context, reducer=iand):
        return reduce(reducer, [self.visit_query(part, field_name) for part in parts]) if parts else Q()

    def visit_or(self, parts, field_name, context):
        return self.visit_and(parts, field_name, context, partial(ior))

    def render_and(self, parts, field_name, context):
        return reduce(iand, parts) if parts else Q()

    def validate_regex(self, value, field_name, context, acceptable_options=('i',)):
        return super(DjangoVisitor, self).validate_regex(value, field_name, context, acceptable_options)
    validate_options = validate_regex

    def visit_regex(self, value, field_name, context):
        if value is Stripped:
            return Skip
        else:
            regex, options = value
            if options & IGNORECASE:
                return Q(("%s__iregex" % field_name, regex))
            else:
                return Q(("%s__regex" % field_name, regex))
    visit_options = visit_regex

to_Q = to_django = DjangoVisitor().visit
