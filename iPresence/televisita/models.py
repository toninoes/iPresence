from django.db import models
from django.contrib.auth.models import User


class Room(models.Model):
	owner = models.ForeignKey(User, unique=True, related_name='owner')
	nombre = models.CharField(max_length=70)
	salaId = models.TextField(blank=True)
	salaIdWebrtc = models.TextField(blank=True)
	autorizado = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='autorizado')
	
	def __unicode__(self):
		return self.nombre
