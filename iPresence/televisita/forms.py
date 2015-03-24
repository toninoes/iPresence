# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.contrib.localflavor.es.forms import *
	

class MyModelChoiceField(forms.ModelChoiceField):
	def label_from_instance(self, obj):
		if obj.es_Alumno:
			rol = 'ALU'
		elif obj.es_tutorLaboral:
			rol = 'LAB'
		elif obj.es_tutorDocente:
			rol = 'DOC'
		return "%s: %s %s" % (rol, obj.first_name, obj.last_name)
		

class AutorizadoForm(forms.Form):
	autorizado = MyModelChoiceField(queryset=User.objects.exclude(is_active=False).exclude(puede_hablar=False).exclude(is_staff=True).order_by("-es_tutorDocente", "-es_tutorLaboral", "-es_Alumno"), empty_label=None)
	enviarMail = forms.BooleanField(initial=False, required=False)
