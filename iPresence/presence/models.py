# -*- coding: utf-8 -*-

from django.db import models
import datetime
from django.contrib.auth.models import User
from django.conf import settings


User.add_to_class('nif', models.CharField(max_length=10, unique=True))
User.add_to_class('es_Alumno', models.BooleanField(default=False))
User.add_to_class('es_tutorDocente', models.BooleanField(default=False))
User.add_to_class('es_tutorLaboral', models.BooleanField(default=False))
User.add_to_class('puede_hablar', models.BooleanField(default=False))
		
		
class EmpresaManager(models.Manager):
	def tutores(self, idEmp):
		empresa = self.get(id=int(idEmp))
		centros = empresa.centro_set.all()
		laborals = Laboral.objects.filter(centro__in=centros)
		return laborals
		
	def alumnosActuales(self, idEmp):
		empresa = self.get(id=int(idEmp))
		centros = empresa.centro_set.all()
		laborals = Laboral.objects.filter(centro__in=centros)
		alumnos = Alumno.objects.filter(laboral__in=laborals, is_active=True)
		return alumnos
		
		
class Empresa(models.Model):
	cif = models.CharField(max_length=10, unique=True)
	nombre = models.CharField(max_length=100, unique=True)
	direccion = models.CharField(max_length=150)
	poblacion = models.CharField(max_length=100)
	postal = models.PositiveIntegerField(max_length=5)
	telefono = models.PositiveIntegerField(max_length=9)
	fax = models.PositiveIntegerField(max_length=9)
	email = models.EmailField()
	objects = EmpresaManager()
	
	def __unicode__(self):
		return self.nombre


class Gerente(models.Model):
	nif = models.CharField(max_length=10, unique=True)
	first_name = models.CharField(max_length=30)
	last_name = models.CharField(max_length=30)
	empresa = models.ForeignKey(Empresa)
	
	def __unicode__(self):
		return u'%s %s' % (self.first_name, self.last_name)


class Centro(models.Model):
	direccion = models.CharField(max_length=150)
	poblacion = models.CharField(max_length=100)
	postal = models.PositiveIntegerField(max_length=5)
	telefono = models.PositiveIntegerField(max_length=9)
	fax = models.PositiveIntegerField(max_length=9)
	email = models.EmailField()
	empresa = models.ForeignKey(Empresa)
	
	def __unicode__(self):
		return u'%s: %s' % (self.poblacion, self.direccion)


class Laboral(User):
	centro = models.ForeignKey(Centro)
	
	def __unicode__(self):
		return u'%s %s' % (self.first_name, self.last_name)
		

class Docente(User):
			
	def __unicode__(self):
		return u'%s %s' % (self.first_name, self.last_name)


class Alumno(User):
	telefono = models.PositiveIntegerField(max_length=9)
	movil = models.PositiveIntegerField(max_length=9)
	fnac = models.DateField(verbose_name='Fecha de nacimiento')
	docente = models.ForeignKey(Docente, blank=True, null=True, on_delete=models.SET_NULL)
	laboral = models.ForeignKey(Laboral, blank=True, null=True, on_delete=models.SET_NULL)
		
	def __unicode__(self):
		return u'%s %s' % (self.first_name, self.last_name)

	def calcula_edad(self):
		dias = 365
		actual_year = datetime.date.today().year
		diff = (datetime.date.today() - self.fnac).days
		if actual_year%4 == 0 and actual_year%100 != 0 or actual_year%400 == 0:
			dias += 1
		edad = str(int(diff/dias))
		return edad
					

class Curso(models.Model):
	fecha_inicio = models.PositiveIntegerField(max_length=4, unique=True)

	def __unicode__(self):
		return u'%s/%s' % (self.fecha_inicio, self.fecha_inicio + 1)


class Aprendizaje(models.Model):
	resultado = models.TextField(max_length=300, verbose_name="Resultado de aprendizaje")
	
	def __unicode__(self):
		return u'%s' % (self.resultado)
				
		
class ContratoPrograma(models.Model):
	MODALIDADES = (
		('A', 'Misma localidad desde 5 Kms'),
		('B', 'Otra localidad hasta 20 Kms'),
		('C', 'Otra localidad a mas de 20 Kms'),
	)
	TRIMESTRES = (
		('1', 'Primer Trimestre'),
		('2', 'Segundo Trimestre'),
		('3', 'Tercer Trimestre'),
	)
	fecha = models.DateField(default=datetime.date.today())
	curso = models.ForeignKey(Curso)
	alumno = models.ForeignKey(Alumno)
	docente = models.ForeignKey(Docente)
	laboral = models.ForeignKey(Laboral)
	gerente = models.ForeignKey(Gerente)
	modalidad = models.CharField(max_length=1, choices=MODALIDADES)
	periodo = models.CharField(max_length=1, choices=TRIMESTRES)
	aprendizajes = models.ManyToManyField(Aprendizaje, verbose_name="Resultados de aprendizaje esperados")
	actividades = models.TextField(max_length=1000, blank=True, verbose_name="Actividades Formativo-Productivas")
	criterios = models.TextField(max_length=1000, blank=True, verbose_name="Criterios de evaluacion")
	confirmado = models.BooleanField(default=False)

	def __unicode__(self):
		return u'Curso: %s Alumno: %s Empresa: %s' % (self.curso, self.alumno, self.gerente.empresa)
				
	
class Seguimiento(models.Model):
	fecha = models.DateField()
	actividad = models.TextField(max_length=200, blank=True)
	tiempo = models.SmallIntegerField()
	observaciones = models.TextField(max_length=200, blank=True)
	contratoprograma = models.ForeignKey(ContratoPrograma)

	def __unicode__(self):
		return u'%s %s %s' % (self.fecha, self.contratoprograma.alumno, self.contratoprograma.gerente.empresa)
		
			
class Visita(models.Model):
	MODALIDADES = (
		('P', 'Presencial'),
		('T', 'Telematica'),
	)
	fecha = models.DateField(default=datetime.date.today())
	contratoprograma = models.ForeignKey(ContratoPrograma)
	aprendizajesPositivos = models.ManyToManyField(Aprendizaje, blank=True, verbose_name="Resultados de aprendizaje esperados definidos en el Contrato-Programa, evaluados positivamente.")
	otro_motivo = models.TextField(max_length=130, blank=True, verbose_name='Si el motivo de la visita es otro o se quiere constatar alguna observación. indicar cuál')
	tiempo = models.CharField(max_length=10, verbose_name='Horas computables como lectivas que se han necesitado para realizar esta visita')
	modalidad = models.CharField(max_length=1, choices=MODALIDADES)
		
	def __unicode__(self):
		return u'Fecha: %s Alumno: %s Empresa: %s' % (self.fecha, self.contratoprograma.alumno, self.contratoprograma.gerente.empresa)
	

class UsuarioInactivo(models.Model):
	usuario = models.ForeignKey(User, unique=True, verbose_name='Usuario a activar')
	key = models.CharField('Clave de activación', max_length=50)
	validez = models.DateTimeField(default=datetime.datetime.now() + datetime.timedelta(days=settings.DIAS_PARA_ACTIVAR_CUENTA))

