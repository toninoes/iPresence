# -*- coding: utf-8 -*-

from django import forms
from django.forms.extras.widgets import SelectDateWidget
from misitio.presence.models import *
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User
#from django.contrib.localflavor.es.forms import *
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext, ugettext_lazy as _
from django.conf import settings
from django.contrib.admin import widgets

import re
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import RegexField
from django.utils.translation import ugettext_lazy as _

ThisYear = date.today().year
YEARS = range(ThisYear - 2, ThisYear + 1)
NACIM = range(ThisYear - 65, ThisYear - 15)

### LocalFlavours Tuneadas ###

def cif_get_checksum(number):
    s1 = sum([int(digit) for pos, digit in enumerate(number) if int(pos) % 2])
    s2 = sum([sum([int(unit) for unit in str(int(digit) * 2)]) for pos, digit in enumerate(number) if not int(pos) % 2])
    return (10 - ((s1 + s2) % 10)) % 10

    
class ESPostalCodeFieldTuned(RegexField):
    """
    A form field that validates its input as a spanish postal code.

    Spanish postal code is a five digits string, with two first digits
    between 01 and 52, assigned to provinces code.
    """
    default_error_messages = {
        'invalid': _('Introduzca un codigo postal valido dentro del rango y formato siguientes: 01XXX - 52XXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(ESPostalCodeFieldTuned, self).__init__(
                r'^(0[1-9]|[1-4][0-9]|5[0-2])\d{3}$',
                max_length, min_length, *args, **kwargs)


class ESPhoneNumberFieldTuned(RegexField):
    """
    A form field that validates its input as a Spanish phone number.
    Information numbers are ommited.

    Spanish phone numbers are nine digit numbers, where first digit is 6 (for
    cell phones), 8 (for special phones), or 9 (for landlines and special
    phones)

    TODO: accept and strip characters like dot, hyphen... in phone number
    """
    default_error_messages = {
        'invalid': _('Introduzca un numero de telefono valido en uno de los siguientes formatos: 6XXXXXXXX, 8XXXXXXXX o 9XXXXXXXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(ESPhoneNumberFieldTuned, self).__init__(r'^(6|7|8|9)\d{8}$',
                max_length, min_length, *args, **kwargs)


class ESIdentityCardNumberFieldTuned(RegexField):
    """
    Spanish NIF/NIE/CIF (Fiscal Identification Number) code.

    Validates three diferent formats:

        NIF (individuals): 12345678A
        CIF (companies): A12345678
        NIE (foreigners): X12345678A

    according to a couple of simple checksum algorithms.

    Value can include a space or hyphen separator between number and letters.
    Number length is not checked for NIF (or NIE), old values start with a 1,
    and future values can contain digits greater than 8. The CIF control digit
    can be a number or a letter depending on company type. Algorithm is not
    public, and different authors have different opinions on which ones allows
    letters, so both validations are assumed true for all types.
    """
    default_error_messages = {
        'invalid': _('Por favor introduzca un NIF, NIE, o CIF valido.'),
        'invalid_only_nif': _('Por favor introduzca un NIF o NIE valido.'),
        'invalid_nif': _('Suma de comprobacion del NIF no valida.'),
        'invalid_nie': _('Suma de comprobacion del NIE no valida.'),
        'invalid_cif': _('Suma de comprobacion del CIF no valida.'),
    }

    def __init__(self, only_nif=False, max_length=None, min_length=None, *args, **kwargs):
        self.only_nif = only_nif
        self.nif_control = 'TRWAGMYFPDXBNJZSQVHLCKE'
        #self.cif_control = 'JABCDEFGHI' 
        self.cif_control = 'JABCDEFGHIJ'        
        #self.cif_types = 'ABCDEFGHKLMNPQS'
        self.cif_types = 'ABCDEFGHJKLMNPQRSUVW'        
        #self.nie_types = 'XT'
        self.nie_types = 'XTYZ'
        id_card_re = re.compile(r'^([%s]?)[ -]?(\d+)[ -]?([%s]?)$' % (self.cif_types + self.nie_types, self.nif_control + self.cif_control), re.IGNORECASE)
        super(ESIdentityCardNumberFieldTuned, self).__init__(id_card_re, max_length, min_length,
                error_message=self.default_error_messages['invalid%s' % (self.only_nif and '_only_nif' or '')],
                *args, **kwargs)

    def clean(self, value):
        super(ESIdentityCardNumberFieldTuned, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        nif_get_checksum = lambda d: self.nif_control[int(d)%23]

        value = value.upper().replace(' ', '').replace('-', '')
        m = re.match(r'^([%s]?)[ -]?(\d+)[ -]?([%s]?)$' % (self.cif_types + self.nie_types, self.nif_control + self.cif_control), value)
        letter1, number, letter2 = m.groups()

        if not letter1 and letter2:
            # NIF
            if letter2 == nif_get_checksum(number):
                return value
            else:
                raise ValidationError(self.error_messages['invalid_nif'])
        elif letter1 in self.nie_types and letter2:
            # NIE
            if letter2 == nif_get_checksum(number):
                return value
            else:
                raise ValidationError(self.error_messages['invalid_nie'])
        elif not self.only_nif and letter1 in self.cif_types and len(number) in [7, 8]:
            # CIF
            if not letter2:
                number, letter2 = number[:-1], int(number[-1])
            checksum = cif_get_checksum(number)
            if letter2 in (checksum, self.cif_control[checksum]):
                return value
            else:
                raise ValidationError(self.error_messages['invalid_cif'])
        else:
            raise ValidationError(self.error_messages['invalid'])              
                

class Autenticar(AuthenticationForm):
	username = forms.CharField(label=_("Username"), max_length=75)
	

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
	autoriza_a = MyModelChoiceField(queryset=User.objects.exclude(is_active=False).exclude(puede_hablar=False).exclude(is_staff=True).order_by("-es_tutorDocente", "-es_tutorLaboral", "-es_Alumno"), empty_label=None)
	enviarMail = forms.BooleanField(initial=False, required=False)
	

class SeguimientoForm(forms.Form):
	TIEMPO = (
		('0', '0 horas'),
		('1', '1 hora'),
		('2', '2 horas'),
		('3', '3 horas'),
		('4', '4 horas'),
		('5', '5 horas'),
		('6', '6 horas'),
		('7', '7 horas'),
		('8', '8 horas'),
		('9', '9 horas'),
		('10', '10 horas'),
		('11', '11 horas'),
		('12', '12 horas'),
		('13', '13 horas'),		
	)
	idSeg = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	#fecha = forms.DateField(widget=SelectDateWidget(years=YEARS))
	fecha = forms.DateField(widget = widgets.AdminDateWidget)
	actividad = forms.CharField(widget=forms.Textarea, max_length=230, required=False)
	tiempo = forms.ChoiceField(widget=forms.Select(), choices=TIEMPO)
	observaciones = forms.CharField(widget=forms.Textarea, required=False, max_length=75)
	contratoprograma = forms.ModelChoiceField(queryset=ContratoPrograma.objects.all().order_by("-curso"))

	def clean_fecha(self):
		fecha = self.cleaned_data['fecha']
		diasemana = fecha.isoweekday()
		meses_dif = timedelta(days=90)
		#if fecha > date.today():
		#	raise forms.ValidationError("Todavía no hemos llegado a esa fecha")
		if (fecha + meses_dif) < date.today():
			raise forms.ValidationError("No puedes seleccionar una fecha con una antigüedad superior a 90 días")
		elif diasemana == 6 or diasemana == 7:
			raise forms.ValidationError("Tienes que seleccionar un día de lunes a viernes")
		
		return fecha


class buscarSeguimientoForm(forms.Form):
	#fecha = forms.DateField(widget=SelectDateWidget(years=YEARS), required=False)
	fecha = forms.DateField(widget = widgets.AdminDateWidget, required=False)
	alumno = forms.ModelChoiceField(queryset=Alumno.objects.all(), required=False)


class registroDocenteForm(forms.Form):
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	email = forms.EmailField(max_length=75)
	
	def clean_nif(self):
		nif = self.cleaned_data['nif']
		usuario = User.objects.filter(nif=nif)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif

	def clean_email(self):
		email = self.cleaned_data['email']
		usuario = User.objects.filter(email=email)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese email")
			
		return email
	
	
class registroAlumnoForm(forms.Form):
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	telefono = ESPhoneNumberFieldTuned()
	movil = ESPhoneNumberFieldTuned()
	#fnac = forms.DateField(widget = widgets.AdminDateWidget, label='Fecha de Nacimiento')
	fnac = forms.DateField(widget=SelectDateWidget(years=NACIM), label='Fecha de Nacimiento')
	email = forms.EmailField(max_length=75)
	
	def clean_nif(self):
		nif = self.cleaned_data['nif']
		usuario = User.objects.filter(nif=nif)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif

	def clean_email(self):
		email = self.cleaned_data['email']
		usuario = User.objects.filter(email=email)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese email")
			
		return email
		

class updateAlumnoForm(forms.Form):
	idUser = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	telefono = ESPhoneNumberFieldTuned()
	movil = ESPhoneNumberFieldTuned()
	fnac = forms.DateField(widget=SelectDateWidget(years=NACIM), label='Fecha de Nacimiento')
	enviarMail = forms.BooleanField(initial=False, required=False)

	def clean_nif(self):
		nif = self.cleaned_data['nif']
		idUser = self.cleaned_data['idUser']
		usuario = User.objects.filter(nif=nif).exclude(id=idUser)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif		

class registroEmpresaForm(forms.Form):
	cif = ESIdentityCardNumberFieldTuned()
	nombre = forms.CharField(max_length=100, label='Razón Social')
	direccion = forms.CharField(max_length=150)
	telefono = ESPhoneNumberFieldTuned()
	fax = ESPhoneNumberFieldTuned()
	poblacion = forms.CharField(max_length=100)
	email = forms.EmailField(max_length=75)
	postal = ESPostalCodeFieldTuned()

	def clean_cif(self):
		cif = self.cleaned_data['cif']
		empresa = Empresa.objects.filter(cif=cif)
		if empresa:
			raise forms.ValidationError("Ya existe una empresa registrada con ese cif")
			
		return cif
		
	def clean_nombre(self):
		nombre = self.cleaned_data['nombre']
		empresa = Empresa.objects.filter(nombre=nombre)
		if empresa:
			raise forms.ValidationError("Ya existe una empresa registrada con ese nombre")
						
		return nombre
		

class updateEmpresaForm(forms.Form):
	idEmp = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	cif = ESIdentityCardNumberFieldTuned()
	nombre = forms.CharField(max_length=100, label='Razón Social')
	direccion = forms.CharField(max_length=150)
	telefono = ESPhoneNumberFieldTuned()
	fax = ESPhoneNumberFieldTuned()
	poblacion = forms.CharField(max_length=100)
	email = forms.EmailField(max_length=75)
	postal = ESPostalCodeFieldTuned()

	def clean_cif(self):
		cif = self.cleaned_data['cif']
		idEmp = self.cleaned_data['idEmp']
		empresa = Empresa.objects.filter(cif=cif).exclude(id=idEmp)
		if empresa:
			raise forms.ValidationError("Ya existe una empresa registrada con ese cif")
			
		return cif
		
	def clean_nombre(self):
		nombre = self.cleaned_data['nombre']
		idEmp = self.cleaned_data['idEmp']
		empresa = Empresa.objects.filter(nombre=nombre).exclude(id=idEmp)
		if empresa:
			raise forms.ValidationError("Ya existe una empresa registrada con ese nombre")
						
		return nombre

		
class registroLaboralForm(forms.Form):
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	email = forms.EmailField(max_length=75)
	centro = forms.ModelChoiceField(queryset=Centro.objects.all())
	
	def clean_nif(self):
		nif = self.cleaned_data['nif']
		usuario = User.objects.filter(nif=nif)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif

	def clean_email(self):
		email = self.cleaned_data['email']
		usuario = User.objects.filter(email=email)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese email")
			
		return email
		
		
class updateLaboralDocenteForm(forms.Form):
	idUser = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	enviarMail = forms.BooleanField(initial=False, required=False)

	def clean_nif(self):
		nif = self.cleaned_data['nif']
		idUser = self.cleaned_data['idUser']
		usuario = User.objects.filter(nif=nif).exclude(id=idUser)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif


class updateLaboralForm(forms.Form):
	idUser = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	email = forms.EmailField(max_length=75)
	enviarMail = forms.BooleanField(initial=False, required=False)

	def clean_nif(self):
		nif = self.cleaned_data['nif']
		idUser = self.cleaned_data['idUser']
		usuario = User.objects.filter(nif=nif).exclude(id=idUser)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese nif")
			
		return nif	

	def clean_email(self):
		email = self.cleaned_data['email']
		idUser = self.cleaned_data['idUser']
		usuario = User.objects.filter(email=email).exclude(id=idUser)
		if usuario:
			raise forms.ValidationError("Ya existe un usuario registrado con ese email")
			
		return email
							

class crearContratoForm(forms.Form):
	MODALIDADES = (
		('', '------------------'),
		('A', 'Misma localidad desde 5 Kms'),
		('B', 'Otra localidad hasta 20 Kms'),
		('C', 'Otra localidad a mas de 20 Kms'),
	)
	TRIMESTRES = (
		('', '------------------'),
		('1', 'Primera Evaluacion'),
		('2', 'Segunda Evaluacion'),
		('3', 'Tercera Evaluacion'),
	)
	curso = forms.ModelChoiceField(queryset=Curso.objects.all().order_by("-id"))
	alumno = forms.ModelChoiceField(queryset=Alumno.objects.exclude(is_active=False))
	docente = forms.ModelChoiceField(queryset=Docente.objects.exclude(is_active=False))
	laboral = forms.ModelChoiceField(queryset=Laboral.objects.exclude(is_active=False))
	gerente = forms.ModelChoiceField(queryset=Gerente.objects.all())
	modalidad = forms.ChoiceField(widget=forms.Select(), choices=MODALIDADES)
	periodo = forms.ChoiceField(widget=forms.Select(), choices=TRIMESTRES)
	aprendizajes = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Aprendizaje.objects.all(), required=False)
	actividades = forms.CharField(widget=forms.Textarea, max_length=1000, required=False)
	criterios = forms.CharField(widget=forms.Textarea, max_length=1000, required=False)

	def clean_alumno(self):
		alumno = self.cleaned_data['alumno']
		curso = self.cleaned_data['curso']
		contratos = ContratoPrograma.objects.filter(curso=curso, alumno=alumno)
		if contratos:
			raise forms.ValidationError("En el curso seleccionado ya existe un Contrato definido para ese alumno")
		
		return alumno


class updateContratoForm(forms.Form):
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
	idCon = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	alumno = forms.ModelChoiceField(queryset=Alumno.objects.exclude(is_active=False))
	laboral = forms.ModelChoiceField(queryset=Laboral.objects.exclude(is_active=False))
	gerente = forms.ModelChoiceField(queryset=Gerente.objects.all())
	modalidad = forms.ChoiceField(widget=forms.Select(), choices=MODALIDADES)
	periodo = forms.ChoiceField(widget=forms.Select(), choices=TRIMESTRES)
	aprendizajes = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Aprendizaje.objects.all(), required=False)
	actividades = forms.CharField(widget=forms.Textarea, max_length=1000, required=False)
	criterios = forms.CharField(widget=forms.Textarea, max_length=1000, required=False)
		
		
class VisitaForm(forms.Form):
	ELEGIR = (
		('SI', 'Si'),
		('NO', 'No'),
	)
	MODALIDADES = (
		('T', 'Telematica'),
		('P', 'Presencial'),
	)
	idVis = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	fecha = forms.DateField(widget = widgets.AdminDateWidget)
	contratoprograma = forms.ModelChoiceField(queryset=ContratoPrograma.objects.all().order_by("-curso"))
	aprendizajesPositivos = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False, queryset=Aprendizaje.objects.all())
	otro_motivo = forms.CharField(widget=forms.Textarea, required=False, max_length=130, label='Si el motivo de la visita es otro o se quiere constatar alguna observación. indicar cuál')
	tiempo = forms.ChoiceField(widget=forms.Select(), choices=([('1', '1 hora'), ('2', '2 horas'), ('3', '3 horas'), ('4', '4 horas'), ('5', '5 horas'), ('6', '6 horas'), ]), label='Tiempo (horas). Horas computables como lectivas que se han necesitado para realizar esta visita')
	modalidad = forms.ChoiceField(widget=forms.Select(), choices=MODALIDADES)
	
	def clean_fecha(self):
		fecha = self.cleaned_data['fecha']
		diasemana = fecha.isoweekday()
		meses_dif = timedelta(days=90)
		#if fecha > date.today():
		#	raise forms.ValidationError("Todavía no hemos llegado a esa fecha")
		if (fecha + meses_dif) < date.today():
			raise forms.ValidationError("No puedes seleccionar una fecha con una antigüedad superior a 90 días")
		elif diasemana == 6 or diasemana == 7:
			raise forms.ValidationError("Tienes que seleccionar un día de lunes a viernes")
		
		return fecha
	
	
class registroGerenteForm(forms.Form):
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	empresa = forms.ModelChoiceField(queryset=Empresa.objects.all())
	
	def clean_nif(self):
		nif = self.cleaned_data['nif']
		gerente = Gerente.objects.filter(nif=nif)
		if gerente:
			raise forms.ValidationError("Ya existe un gerente registrado con ese nif")
			
		return nif


class updateGerenteForm(forms.Form):
	idGer = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	nif = ESIdentityCardNumberFieldTuned()
	first_name = forms.CharField(max_length=30, label='Nombre')
	last_name = forms.CharField(max_length=30, label='Apellido/s')
	
	def clean_nif(self):
		nif = self.cleaned_data['nif']
		idGer = self.cleaned_data['idGer']
		gerente = Gerente.objects.filter(nif=nif).exclude(id=idGer)
		if gerente:
			raise forms.ValidationError("Ya existe un gerente registrado con ese nif")
			
		return nif
		
	
class registroCentroForm(forms.Form):
	direccion = forms.CharField(max_length=150)
	poblacion = forms.CharField(max_length=100)
	postal = ESPostalCodeFieldTuned()
	telefono = ESPhoneNumberFieldTuned()
	fax = ESPhoneNumberFieldTuned()
	email = forms.EmailField(max_length=75)
	empresa = forms.ModelChoiceField(queryset=Empresa.objects.all())
	

class updateCentroForm(forms.Form):
	idCen = forms.CharField(widget=forms.HiddenInput(), required=False, label='')
	direccion = forms.CharField(max_length=150)
	poblacion = forms.CharField(max_length=100)
	postal = ESPostalCodeFieldTuned()
	telefono = ESPhoneNumberFieldTuned()
	fax = ESPhoneNumberFieldTuned()
	email = forms.EmailField(max_length=75)
	
	
class restaurarPasswordForm(forms.Form):
	email = forms.EmailField(max_length=75)

	def clean_email(self):
		email = self.cleaned_data['email']
		try:
			usuario = User.objects.get(email=email)
		except:
			raise forms.ValidationError("No existe ningún usuario con ese e-mail")
			
		if not usuario.is_active:
			raise forms.ValidationError("El actual usuario está inactivo")

		usuarioInactivo = UsuarioInactivo.objects.filter(usuario=usuario)
		if usuarioInactivo:
			usuarioInactivo = UsuarioInactivo.objects.get(usuario=usuario)
			if datetime.now() <= usuarioInactivo.validez:
				raise forms.ValidationError("Ya se ha envió un mail para recuperar la contraseña a este usuario intentelo dentro de "+str(settings.DIAS_PARA_ACTIVAR_CUENTA)+" días.")
				
		return email
