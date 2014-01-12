from django.db import models

# Create your models here.
class MyModel(models.Model):
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=10)

