from __future__ import unicode_literals

from django.db import models

class MyManager(models.Manager):
    def clean_and_create(self, list_of_tuples):
        self.all().delete()
        self.bulk_create([
            self.model(field1=f1, field2=f2) for f1, f2 in list_of_tuples
        ])

class MyModel(models.Model):
    field1 = models.IntegerField(null=True)
    field2 = models.CharField(max_length=10)

    objects = MyManager()

    def __str__(self):
        return "field1=%s, field2='%s'" % (self.field1, self.field2)
