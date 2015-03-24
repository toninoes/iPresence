# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404
from misitio.presence.models import *
from misitio.presence.forms import *
from django.http import HttpResponse, HttpResponseRedirect
from datetime import timedelta, date, datetime
from time import strftime, strptime
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.template import RequestContext
from django.contrib import auth
from django.contrib.auth.models import User
import ho.pisa as pisa
import cStringIO as StringIO
import cgi
from django.template.loader import render_to_string
from django.contrib.auth.forms import SetPasswordForm
from django.core.mail import EmailMessage
from django.contrib.sites.models import get_current_site
from django.template.response import TemplateResponse
import urlparse
from django.contrib.auth import login as auth_login
from django.conf import settings
from misitio.Pubnub import Pubnub


PUBNUB_PUBLISH_KEY = '----'
PUBNUB_SUBSCRIBE_KEY = '-----'
PUBNUB_SECRET_KEY = '----'


def presence(request):

	return render_to_response('inicio.html', context_instance=RequestContext(request))


def rangeWeek(fecha):
	weekday = fecha.isoweekday()
	lunes = fecha + timedelta(days=1 - weekday)
	viernes = fecha + timedelta(days=5 - weekday)

	return (lunes, viernes)


def generar_pdf(html, nombrepdf='descarga'):
	result = StringIO.StringIO()
	pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result)
	nombrepdf = nombrepdf.replace(' ', '_')
	if not pdf.err:
		response = HttpResponse(result.getvalue(), mimetype='application/pdf')
		response['Content-Disposition'] = 'attachment; filename=' + nombrepdf + '.pdf'
		return response
	return HttpResponse('Error al generar el PDF: %s' % cgi.escape(html))


@login_required
def entrarsalir(request, txt):
	if not request.user.is_staff:
		pubnub = Pubnub(PUBNUB_PUBLISH_KEY, PUBNUB_SUBSCRIBE_KEY, PUBNUB_SECRET_KEY, True)
		pubnub.publish({
			'channel': 'entrarsalir',
			'message': txt + request.user.get_full_name()
		})


@csrf_protect
@never_cache
def entrar(request, template_name='registration/login.html',
			redirect_field_name=auth.REDIRECT_FIELD_NAME,
			authentication_form=Autenticar,
			current_app=None, extra_context=None):

	redirect_to = request.REQUEST.get(redirect_field_name, '')

	if request.method == "POST":
		form = authentication_form(data=request.POST)
		if form.is_valid():
			netloc = urlparse.urlparse(redirect_to)[1]

			if not redirect_to:
				redirect_to = settings.LOGIN_REDIRECT_URL

			elif netloc and netloc != request.get_host():
				redirect_to = settings.LOGIN_REDIRECT_URL

			auth_login(request, form.get_user())

			if request.session.test_cookie_worked():
				request.session.delete_test_cookie()
			####Voy a avisar de que ya he entrado !!!!!
			entrarsalir(request, 'CONECTADO' + '<br/>')
			#return HttpResponseRedirect(redirect_to)
			if request.user.es_Alumno or request.user.es_tutorDocente or request.user.es_tutorLaboral:
				return HttpResponseRedirect('/verSeguimiento/')
			else:
				return HttpResponseRedirect('/panel/')
	else:
		form = authentication_form(request)

	request.session.set_test_cookie()

	current_site = get_current_site(request)

	context = {
		'form': form,
		redirect_field_name: redirect_to,
		'site': current_site,
		'site_name': current_site.name,
	}
	if extra_context is not None:
		context.update(extra_context)

	return TemplateResponse(request, template_name, context, current_app=current_app)


@login_required
def salir(request):
	entrarsalir(request, 'DESCONECTADO' + '<br/>')
	auth.logout(request)
	return HttpResponseRedirect('/')


@login_required
def error(request, num):
	error = {
		'0': 'No estás autorizado a realizar esa operación',
		'1': 'No perteneces al grupo de Alumnos',
		'2': 'No perteneces al grupo de Docentes',
		'3': 'Ya existe un usuario con ese mismo NIF o e-mail',
		'4': 'Ya existe una empresa con ese CIF o que se llama igual',
		'5': 'Ha ocurrido un error en el envío del correo electrónico',
		'6': 'Sólo el administrador de i-Presence puede realizar esa operación',
		'7': 'No estas autorizado a realizar videoconferencias',
		'8': 'Ya tienes un registro con esa misma fecha.',
		'9': 'Tienes que seleccionar un día de lunes a viernes',
		'10': 'No ha podido darse de alta ese contrato',
		'11': 'En el curso seleccionado ya existe un Contrato definido para ese alumno',
		'12': 'No se han podido registrar los Resultados de aprendizaje esperados para ese alumno',
		'13': 'No eres el actual Tutor de este alumno',
		'14': 'Todavía no hemos llegado a esa fecha',
		'15': 'Tienes que elegir a un alumno',
		'16': 'Han finalizado los ' + str(settings.DIAS_PARA_ACTIVAR_CUENTA) + ' días para activar tu cuenta.'
	}

	return render_to_response('error.html', {'error': error[num]}, context_instance=RequestContext(request))


@login_required
def panel(request):
	alumno = None
	if request.user.es_Alumno:
		alumno = get_object_or_404(Alumno, id=request.user.id)
	return render_to_response('panel.html', {'alumno': alumno}, context_instance=RequestContext(request))


################### FICHA SEGUIMIENTO ###################

@login_required
def FichaPdf(request):

	if request.user.es_tutorDocente or request.user.es_Alumno:
		if request.method == 'POST':
			form = buscarSeguimientoForm(request.POST)
			if form.is_valid():
				if request.user.es_tutorDocente:
					alumno = form.cleaned_data['alumno']
					if not alumno:
						return HttpResponseRedirect('/error/15/')
				else:
					alumno = request.user.alumno
				contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")

				if form.cleaned_data['fecha']:
					rango = rangeWeek(form.cleaned_data['fecha'])
				else:
					rango = rangeWeek(date.today())
				seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos, fecha__range=(rango[0], rango[1])).order_by("fecha")

				if seguimientos:
					contrato = seguimientos[0].contratoprograma
				else:
					contrato = None

				html = render_to_string('seguimientos/FichaPdf.html', {'proyecto': settings.PROJECT_PATH, 'pagesize': 'A4', 'seguimientos': seguimientos, 'contrato': contrato, 'lunes': rango[0], 'viernes': rango[1], 'alumno': alumno}, context_instance=RequestContext(request))
				nombrepdf = 'Ficha_Semanal_' + str(alumno) + '_' + str(rango[0]) + '_' + str(rango[1])
				return generar_pdf(html, nombrepdf)
		else:
			return HttpResponseRedirect('/error/0/')
	else:
		return HttpResponseRedirect('/error/1/')


@login_required
def insertarSeguimiento(request):

	if request.user.es_Alumno:
		alumno = request.user.alumno
		contrato = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")[0]
		if request.method == 'POST':
			form = SeguimientoForm(request.POST)
			if form.is_valid():
				seguimiento = Seguimiento.objects.filter(fecha=form.cleaned_data['fecha'], contratoprograma=form.cleaned_data['contratoprograma']).count()
				if seguimiento > 0:
					return HttpResponseRedirect('/error/8/')
				else:
					Seguimiento.objects.create(fecha=form.cleaned_data['fecha'], actividad=form.cleaned_data['actividad'],
												tiempo=form.cleaned_data['tiempo'], observaciones=form.cleaned_data['observaciones'],
												contratoprograma=form.cleaned_data['contratoprograma'])
				return HttpResponseRedirect('/verSeguimiento/')
		else:
			form = SeguimientoForm(initial={'fecha': '', 'actividad': '', 'observaciones': ''})
		return render_to_response('seguimientos/insertarSeguimiento.html', {'form': form, 'contrato': contrato}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/1/')


@login_required
def editarSeguimiento(request, idSeg):
	if request.user.es_Alumno:
		alumno = request.user.alumno
		contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
		seguimiento = get_object_or_404(Seguimiento, id=int(idSeg), contratoprograma__in=contratos)
		if request.method == 'POST':
			form = SeguimientoForm(request.POST)
			if form.is_valid():
				seguimiento = Seguimiento.objects.filter(fecha=form.cleaned_data['fecha'], contratoprograma=form.cleaned_data['contratoprograma']).exclude(id=form.cleaned_data['idSeg']).count()
				if seguimiento > 0:
					return HttpResponseRedirect('/error/8/')
				else:
					seguimiento = Seguimiento.objects.filter(id=form.cleaned_data['idSeg']).update(fecha=form.cleaned_data['fecha'], actividad=form.cleaned_data['actividad'], tiempo=form.cleaned_data['tiempo'], observaciones=form.cleaned_data['observaciones'])
				return HttpResponseRedirect('/verSeguimiento/')
		else:
			form = SeguimientoForm(initial={'idSeg': seguimiento.id, 'fecha': seguimiento.fecha,
											'actividad': seguimiento.actividad, 'tiempo': seguimiento.tiempo,
											'observaciones': seguimiento.observaciones})
		return render_to_response('seguimientos/editarSeguimiento.html', {'form': form, 'contrato': seguimiento.contratoprograma}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/1/')


@login_required
def Calculo_diasYhoras(request, seguimientos):
	dias = 0
	horas = 0
	for seguimiento in seguimientos:
		if seguimiento.tiempo > 0:
			dias += 1
			horas += seguimiento.tiempo

	return (dias, horas)


@login_required
def verSeguimiento(request, idAlu=None):
	lunes, viernes, seguimientos, alumno, alumnos, fecha, verTodos = [None, None, None, None, None, None, None]
	if request.user.es_Alumno:
		diasYhoras = (0,0)
		alumno = request.user.alumno
		contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
		if request.method == 'POST':
			form = buscarSeguimientoForm(request.POST)
			if form.is_valid():
				if not form.cleaned_data['fecha']:
					seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-fecha")
					diasYhoras = Calculo_diasYhoras (request, seguimientos)
				else:
					lunes, viernes = rangeWeek(form.cleaned_data['fecha'])
					seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos, fecha__range=(lunes, viernes)).order_by("-fecha")
					form = buscarSeguimientoForm(initial={'fecha': form.cleaned_data['fecha']})

		else:
			form = buscarSeguimientoForm()
			seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-fecha")
			diasYhoras = Calculo_diasYhoras (request, seguimientos)

		if seguimientos:
			contrato = seguimientos[0].contratoprograma
		else:
			contrato = None

		return render_to_response('seguimientos/verSeguimiento.html', {'seguimientos': seguimientos, 'dias': diasYhoras[0], 'horas': diasYhoras[1], 'contrato': contrato, 'form': form, 'lunes': lunes, 'viernes': viernes,  'alumno': alumno}, context_instance=RequestContext(request))

	elif request.user.es_tutorDocente or request.user.es_tutorLaboral:
		try:
			alumnos = request.user.docente.alumno_set.all().order_by("-id")
		except:
			alumnos = request.user.laboral.alumno_set.all().order_by("-id")
		contratos = ContratoPrograma.objects.filter(alumno__in=alumnos).order_by("-curso")
		if request.method == 'POST':
			form = buscarSeguimientoForm(request.POST)
			if form.is_valid():
				alumno = form.cleaned_data['alumno']
				if not form.cleaned_data['fecha']:
					if alumno:
						contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
						seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-fecha")
					else:
						seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-fecha")
						verTodos = True
				else:
					lunes, viernes = rangeWeek(form.cleaned_data['fecha'])
					if alumno:
						contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
						seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos, fecha__range=(lunes, viernes)).order_by("-fecha")
					else:
						seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos, fecha__range=(lunes, viernes)).order_by("-fecha")
						verTodos = True
					form = buscarSeguimientoForm(initial={'fecha': form.cleaned_data['fecha']})
		else:
			form = buscarSeguimientoForm()
			if idAlu:
				alumno = get_object_or_404(Alumno, id=int(idAlu))
				if request.user.es_tutorDocente:
					if alumno.docente == None:
						return HttpResponseRedirect('/error/13/')
					elif alumno.docente.id != request.user.id:
						return HttpResponseRedirect('/error/13/')
				else:
					if alumno.laboral == None:
						return HttpResponseRedirect('/error/13/')
					if alumno.laboral.id != request.user.id:
						return HttpResponseRedirect('/error/13/')

				contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
				seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-fecha")
			else:
				seguimientos = Seguimiento.objects.filter(contratoprograma__in=contratos).order_by("-contratoprograma", "-fecha")
				verTodos = True
		return render_to_response('seguimientos/verSeguimientoDoc.html', {'seguimientos': seguimientos, 'form': form, 'lunes': lunes, 'viernes': viernes, 'alumnos': alumnos, 'alumno': alumno, 'verTodos': verTodos}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/0/')


@login_required
def borrarSeguimiento(request, idSeg):

	if request.user.es_Alumno:
		alumno = request.user.alumno
		contratos = ContratoPrograma.objects.filter(alumno=alumno)
		seguimiento = get_object_or_404(Seguimiento, id=int(idSeg), contratoprograma__in=contratos)
		seguimiento.delete()
	else:
		return HttpResponseRedirect('/error/1/')

	return HttpResponseRedirect('/verSeguimiento/')

################### FIN FICHA SEGUIMIENTO ###################


################### REGISTRO USUARIOS ###################


@login_required
def cambioPassword(request):
	if request.method == 'POST':
		form = SetPasswordForm(request.user, request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect("/panel/")
	else:
		form = SetPasswordForm(request.user)
	return render_to_response("registration/password_set_form.html", {'form': form}, context_instance=RequestContext(request))


@login_required
def updateUser(request):
	if request.user.es_Alumno:
		alumno = get_object_or_404(Alumno, id=request.user.id)
		if request.method == 'POST':
			form = updateAlumnoForm(request.POST)
			if form.is_valid():
				try:
					Alumno.objects.filter(id=request.user.id).update(first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'], nif=form.cleaned_data['nif'], telefono=form.cleaned_data['telefono'],
						movil=form.cleaned_data['movil'], fnac=form.cleaned_data['fnac'])
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')
				return HttpResponseRedirect('/updateComplete/')
		else:
			form = updateAlumnoForm(initial={'first_name': request.user.first_name, 'last_name': request.user.last_name,
												'nif': request.user.nif, 'telefono': alumno.telefono, 'movil': alumno.movil,
												'fnac': alumno.fnac, 'idUser': request.user.id})
	else:
		if request.method == 'POST':
			form = updateLaboralDocenteForm(request.POST)
			if form.is_valid():
				try:
					User.objects.filter(id=request.user.id).update(first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'],
										nif=form.cleaned_data['nif'])
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')
				return HttpResponseRedirect('/updateComplete/')
		else:
			form = updateLaboralDocenteForm(initial={'first_name': request.user.first_name, 'last_name': request.user.last_name, 'nif': request.user.nif,
											'idUser': request.user.id})

	return render_to_response('registration/update_register.html', {'form': form}, context_instance=RequestContext(request))


@login_required
def updateComplete(request):
	return render_to_response('registration/update_complete.html', context_instance=RequestContext(request))


@login_required
def confirmarAlta(request, usuario_confirmado):
	dicc = {'usuario_confirmado': usuario_confirmado, 'servidor': settings.SERVER}
	asunto = render_to_string('registration/confirmar_usuario_asunto.txt', dicc)
	mensaje = render_to_string('registration/confirmar_usuario_mensaje.txt', dicc)
	email = EmailMessage(asunto, mensaje, to=[usuario_confirmado.email])
	email.send()


def activar(request, key):
	inactivo = get_object_or_404(UsuarioInactivo, key=key)
	reactivar = None
	if inactivo.validez >= datetime.now():
		password = User.objects.make_random_password(length=50)
		usuario = inactivo.usuario
		inactivo.delete()
		usuario.set_password(password)
		usuario.save()
		usuario = auth.authenticate(username=usuario.username, password=password)
		if usuario is not None and usuario.is_active:
			auth.login(request, usuario)
			confirmarAlta(request, usuario)
			form = SetPasswordForm(request.user)
			return render_to_response("registration/password_set_form.html", {'form': form}, context_instance=RequestContext(request))
		else:
			return HttpResponseRedirect("/")
	else:
		inactivo.delete()
		form = restaurarPasswordForm()
		reactivar = True
		return render_to_response("registration/restaurar_usuario.html", {'form': form, 'reactivar': reactivar}, context_instance=RequestContext(request))


def comunicarRestaurarPassword(request, destinatario, key, email):
	dicc = {'usuario': destinatario,
			'dias_activar': settings.DIAS_PARA_ACTIVAR_CUENTA,
			'key': key,
			'servidor': settings.SERVER}
	asunto = render_to_string('registration/restaurar_usuario_asunto.txt', dicc)
	mensaje = render_to_string('registration/restaurar_usuario_mensaje.txt', dicc)
	email = EmailMessage(asunto, mensaje, to=[email])
	email.send()


def restaurarPassword(request):
	email = None
	if request.method == 'POST':
		form = restaurarPasswordForm(request.POST)
		if form.is_valid():
			usuario = User.objects.get(email=form.cleaned_data['email'])
			#try:
			key = User.objects.make_random_password(length=50)
			usuarioInactivo = UsuarioInactivo.objects.filter(usuario=usuario)
			if usuarioInactivo:
				usuarioInactivo = UsuarioInactivo.objects.get(usuario=usuario)
				if usuarioInactivo.validez < datetime.now():
					UsuarioInactivo.objects.filter(usuario=usuario).update(key=key, validez=datetime.now() + timedelta(days=settings.DIAS_PARA_ACTIVAR_CUENTA))
			else:
				UsuarioInactivo.objects.create(usuario=usuario, key=key)
			#except:
			#	return HttpResponseRedirect('/error/3/')

			try:
				comunicarRestaurarPassword(request, usuario.first_name, key, usuario.email)
			except:
				return HttpResponseRedirect('/error/5/')

			email = usuario.email
	else:
		form = restaurarPasswordForm()

	return render_to_response("registration/restaurar_usuario.html", {'form': form, 'email': email}, context_instance=RequestContext(request))


@login_required
def comunicarAlta(request, destinatario, key, email):
	dicc = {'nuevo_usuario': destinatario,
			'dias_activar': settings.DIAS_PARA_ACTIVAR_CUENTA,
			'key': key,
			'servidor': settings.SERVER}
	asunto = render_to_string('registration/activar_usuario_asunto.txt', dicc)
	mensaje = render_to_string('registration/activar_usuario_mensaje.txt', dicc)
	email = EmailMessage(asunto, mensaje, to=[email])
	email.send()


@login_required
def registroAlumno(request):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			form = registroAlumnoForm(request.POST)
			if form.is_valid():
				try:
					alumno = Alumno.objects.create(
								username=form.cleaned_data['email'], first_name=form.cleaned_data['first_name'],
								last_name=form.cleaned_data['last_name'], email=form.cleaned_data['email'],
								nif=form.cleaned_data['nif'], telefono=form.cleaned_data['telefono'],
								movil=form.cleaned_data['movil'], fnac=form.cleaned_data['fnac'],
								es_Alumno=True, puede_hablar=True)
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')

				try:
					key = User.objects.make_random_password(length=50)
					UsuarioInactivo.objects.create(usuario=alumno, key=key)
				except:
					return HttpResponseRedirect('/error/3/')

				try:
					comunicarAlta(request, form.cleaned_data['first_name'], key, form.cleaned_data['email'])
				except:
					return HttpResponseRedirect('/error/5/')

				return HttpResponseRedirect('/verAlumnos/')
		else:
			form = registroAlumnoForm()
		return render_to_response("registration/register.html", {'form': form, 'newuser': 'alumno'}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def registroLaboral(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			form = registroLaboralForm(request.POST)
			if form.is_valid():
				try:
					laboral = Laboral.objects.create(
								username=form.cleaned_data['email'], first_name=form.cleaned_data['first_name'],
								last_name=form.cleaned_data['last_name'], email=form.cleaned_data['email'],
								nif=form.cleaned_data['nif'], centro=form.cleaned_data['centro'], es_tutorLaboral=True,
								puede_hablar=True)
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')

				#try:
				#	key = User.objects.make_random_password(length=50)
				#	UsuarioInactivo.objects.create(usuario=laboral, key=key)
				#except:
				#	return HttpResponseRedirect('/error/3/') ###

				#try:
				#	comunicarAlta(request, form.cleaned_data['first_name'], key, form.cleaned_data['email'])
				#except:
				#	return HttpResponseRedirect('/error/5/')

				return HttpResponseRedirect('/verLaborals/')
		else:
			form = registroLaboralForm()

		if idEmp:
			empresa = get_object_or_404(Empresa, id=int(idEmp))
			centros = empresa.centro_set.all()
		else:
			empresa = None
			centros = None
		return render_to_response("registration/register.html", {'form': form, 'newuser': 'laboral', 'centros': centros, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarLaboral(request, idUser):
	if request.user.es_tutorDocente or request.user.is_staff:
		laboral = get_object_or_404(Laboral, id=int(idUser))
		if request.method == 'POST':
			form = updateLaboralForm(request.POST)
			if form.is_valid():
				User.objects.filter(id=laboral.id).update(first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'],
										nif=form.cleaned_data['nif'], username=form.cleaned_data['email'], email=form.cleaned_data['email'])

				return HttpResponseRedirect('/verLaborals/' + str(laboral.centro.empresa.id) + '/')

		else:
			form = updateLaboralForm(initial={'first_name': laboral.first_name, 'last_name': laboral.last_name, 'nif': laboral.nif,
											'idUser': laboral.id, 'email': laboral.email,})

		return render_to_response('registration/update_laboral_register.html', {'form': form}, context_instance=RequestContext(request))

	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def registroDocente(request):
	if request.user.is_staff:
		if request.method == 'POST':
			form = registroDocenteForm(request.POST)
			if form.is_valid():
				try:
					docente = Docente.objects.create(
								username=form.cleaned_data['email'], first_name=form.cleaned_data['first_name'],
								last_name=form.cleaned_data['last_name'], email=form.cleaned_data['email'],
								nif=form.cleaned_data['nif'], es_tutorDocente=True, puede_hablar=True)
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')

				try:
					key = User.objects.make_random_password(length=50)
					UsuarioInactivo.objects.create(usuario=docente, key=key)
				except:
					return HttpResponseRedirect('/error/3/')

				try:
					comunicarAlta(request, form.cleaned_data['first_name'], key, form.cleaned_data['email'])
				except:
					return HttpResponseRedirect('/error/5/')

				return HttpResponseRedirect('/verDocentes/')
		else:
			form = registroDocenteForm()
		return render_to_response("registration/register.html", {'form': form, 'newuser': 'docente'}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/6/')


@login_required
def registroCompleto(request):
	return render_to_response('registration/register_complete.html', context_instance=RequestContext(request))


@login_required
def verAlumnos(request):
	if request.user.es_tutorDocente or request.user.es_tutorLaboral or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			if request.user.es_tutorLaboral:
				alumnos = request.user.laboral.alumno_set.all()
			elif request.user.es_tutorDocente:
				alumnos = Alumno.objects.all()
				#alumnos = request.user.docente.alumno_set.all()
			else:
				alumnos = Alumno.objects.all().order_by("-is_active", "-id")
		return render_to_response('alumnos/verAlumnos.html', {'alumnos': alumnos}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def activaUsuario(request, idUsu):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'GET':
			usuario = get_object_or_404(User, id=int(idUsu))
			if usuario.es_tutorDocente and request.user.es_tutorDocente:
				return HttpResponseRedirect('/error/6/')
			User.objects.filter(id=int(idUsu)).update(is_active=True)
		if usuario.es_Alumno:
			return HttpResponseRedirect('/verAlumnos/')
		elif usuario.es_tutorDocente:
			return HttpResponseRedirect('/verDocentes/')
		else:
			return HttpResponseRedirect('/verLaborals/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def desactivaUsuario(request, idUsu):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'GET':
			usuario = get_object_or_404(User, id=int(idUsu))
			if usuario.es_tutorDocente and request.user.es_tutorDocente:
				return HttpResponseRedirect('/error/6/')
			User.objects.filter(id=int(idUsu)).update(is_active=False)
		if usuario.es_Alumno:
			return HttpResponseRedirect('/verAlumnos/')
		elif usuario.es_tutorDocente:
			return HttpResponseRedirect('/verDocentes/')
		else:
			return HttpResponseRedirect('/verLaborals/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def hablaUsuario(request, idUsu):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'GET':
			usuario = get_object_or_404(User, id=int(idUsu))
			if usuario.es_tutorDocente and request.user.es_tutorDocente:
				return HttpResponseRedirect('/error/6/')
			User.objects.filter(id=int(idUsu)).update(puede_hablar=True)
		if usuario.es_Alumno:
			return HttpResponseRedirect('/verAlumnos/')
		elif usuario.es_tutorDocente:
			return HttpResponseRedirect('/verDocentes/')
		else:
			return HttpResponseRedirect('/verLaborals/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def nohablaUsuario(request, idUsu):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'GET':
			usuario = get_object_or_404(User, id=int(idUsu))
			if usuario.es_tutorDocente and request.user.es_tutorDocente:
				return HttpResponseRedirect('/error/6/')
			User.objects.filter(id=int(idUsu)).update(puede_hablar=False)
		if usuario.es_Alumno:
			return HttpResponseRedirect('/verAlumnos/')
		elif usuario.es_tutorDocente:
			return HttpResponseRedirect('/verDocentes/')
		else:
			return HttpResponseRedirect('/verLaborals/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verAlumnosEmpresa(request, idEmp):
	if request.user.es_tutorDocente or request.user.es_tutorLaboral or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			empresa = get_object_or_404(Empresa, id=int(idEmp))
			alumnos = Empresa.objects.alumnosActuales(idEmp)
		return render_to_response('alumnos/verAlumnos.html', {'alumnos': alumnos, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verLaborals(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			if idEmp:
				empresa = get_object_or_404(Empresa, id=int(idEmp))
				laborals = Empresa.objects.tutores(idEmp)
			else:
				empresa = None
				laborals = Laboral.objects.all()
		return render_to_response('laborales/verLaborals.html', {'laborals': laborals, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verDocentes(request):
	if request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			docentes = Docente.objects.all()
		return render_to_response('docentes/verDocentes.html', {'docentes': docentes}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/6/')

################### FIN REGISTRO USUARIOS ###################


################### EMPRESA ###################


@login_required
def registroEmpresa(request):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			form = registroEmpresaForm(request.POST)
			if form.is_valid():
				try:
					empresa = Empresa.objects.create(cif=form.cleaned_data['cif'], nombre=form.cleaned_data['nombre'],
														direccion=form.cleaned_data['direccion'], telefono=form.cleaned_data['telefono'],
														fax=form.cleaned_data['fax'],  poblacion=form.cleaned_data['poblacion'],
														email=form.cleaned_data['email'],  postal=form.cleaned_data['postal'])

					Centro.objects.create(direccion=form.cleaned_data['direccion'], telefono=form.cleaned_data['telefono'],
											fax=form.cleaned_data['fax'],  poblacion=form.cleaned_data['poblacion'],
											email=form.cleaned_data['email'],  postal=form.cleaned_data['postal'], empresa=empresa)

				except IntegrityError:
					return HttpResponseRedirect('/error/4/')

				return HttpResponseRedirect('/verEmpresas/')
		else:
			form = registroEmpresaForm()
		return render_to_response("empresas/registroEmpresa.html", {'form': form}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarEmpresa(request, idEmp):
	if request.user.es_tutorDocente or request.user.is_staff:
		empresa = get_object_or_404(Empresa, id=int(idEmp))
		if request.method == 'POST':
			form = updateEmpresaForm(request.POST)
			if form.is_valid():
				empresa = Empresa.objects.filter(id=form.cleaned_data['idEmp']).update(cif=form.cleaned_data['cif'],
													nombre=form.cleaned_data['nombre'], direccion=form.cleaned_data['direccion'],
													telefono=form.cleaned_data['telefono'], fax=form.cleaned_data['fax'],
													poblacion=form.cleaned_data['poblacion'], email=form.cleaned_data['email'],
													postal=form.cleaned_data['postal'])
				return HttpResponseRedirect('/verEmpresas/')
		else:
			form = updateEmpresaForm(initial={'idEmp': empresa.id, 'cif': empresa.cif, 'nombre': empresa.nombre,
													'direccion': empresa.direccion, 'telefono': empresa.telefono, 'fax': empresa.fax,
													'poblacion': empresa.poblacion, 'email': empresa.email, 'postal': empresa.postal,})
		return render_to_response('empresas/editarEmpresa.html', {'form': form}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verEmpresas(request):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			empresas = Empresa.objects.all().order_by("nombre")
		return render_to_response('empresas/verEmpresas.html', {'empresas': empresas}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


################### FIN EMPRESA ###################


################### CONTRATO Y PROGRAMA_FORMATIVO ###################

@login_required
def alumnosSinContrato(request, curso):
	alumnosSincontrato = []
	for alumno in Alumno.objects.exclude(is_active=False):
		contratos = ContratoPrograma.objects.filter(curso=curso, alumno=alumno)
		if not contratos:
			alumnosSincontrato.append(alumno)

	return alumnosSincontrato


@login_required
def compruebaCurso(request):
	mesactual = strftime("%m")
	yearActual = int(strftime("%Y"))

	if mesactual in ('01','02','03','04','05','06'):
		try:
			curso = Curso.objects.get(fecha_inicio=yearActual-1)
		except:
			Curso.objects.create(fecha_inicio=yearActual-1)
	elif mesactual in ('09','10','11','12'):
		try:
			curso = Curso.objects.get(fecha_inicio=yearActual)
		except:
			Curso.objects.create(fecha_inicio=yearActual)


@login_required
def confirmaContrato(request, idCont):
	if request.user.es_tutorDocente:
		if request.method == 'GET':
			contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
			if contrato.docente.id == request.user.id:
				ContratoPrograma.objects.filter(id=int(idCont)).update(confirmado=True)

		return HttpResponseRedirect('/verContratos/' + str(contrato.gerente.empresa.id) + '/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def desconfirmaContrato(request, idCont):
	if request.user.es_tutorDocente:
		if request.method == 'GET':
			contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
			if contrato.docente.id == request.user.id:
				ContratoPrograma.objects.filter(id=int(idCont)).update(confirmado=False)
		return HttpResponseRedirect('/verContratos/' + str(contrato.gerente.empresa.id) + '/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def ProgramaPdf(request, idCont):
	if request.user.es_tutorDocente:
		if request.method == 'GET':
			programa = get_object_or_404(ContratoPrograma, id=int(idCont))
			aprendizajes = programa.aprendizajes.all()
			html = render_to_string('contratos-programas/ProgramaPdf.html', {'proyecto': settings.PROJECT_PATH, 'pagesize': 'A4', 'programa': programa, 'aprendizajes': aprendizajes}, context_instance=RequestContext(request))
			nombrepdf = 'Programa_Formativo_' + str(programa.curso) + '_' + str(programa.alumno)
			return generar_pdf(html, nombrepdf)
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def ContratoPdf(request, idCont):
	if request.user.es_tutorDocente:
		if request.method == 'GET':
			contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
			html = render_to_string('contratos-programas/ContratoPdf.html', {'pagesize': 'A4', 'contrato': contrato}, context_instance=RequestContext(request))
			nombrepdf = 'Datos_Contrato_' + str(contrato.curso) + '_' + str(contrato.alumno)
			return generar_pdf(html, nombrepdf)
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def crearContrato(request, idEmp):
	if request.user.es_tutorDocente:
		empresa = get_object_or_404(Empresa, id=int(idEmp))
		gerentes = empresa.gerente_set.all()
		laborals = Empresa.objects.tutores(idEmp)
		alumnos = None

		if request.method == 'POST':
			form = crearContratoForm(request.POST)
			if form.is_valid():
				contratos = ContratoPrograma.objects.filter(curso=form.cleaned_data['curso'], alumno=form.cleaned_data['alumno']).count()
				if contratos > 0:
					return HttpResponseRedirect('/error/11/')
				else:
					try:
						contrato = ContratoPrograma.objects.create(alumno=form.cleaned_data['alumno'],
									curso=form.cleaned_data['curso'], docente=form.cleaned_data['docente'],
									laboral=form.cleaned_data['laboral'], gerente=form.cleaned_data['gerente'],
									modalidad=form.cleaned_data['modalidad'], periodo=form.cleaned_data['periodo'],
									actividades=form.cleaned_data['actividades'], criterios=form.cleaned_data['criterios'])
					except:
						return HttpResponseRedirect('/error/10/')

					try:
						for aprendizaje in form.cleaned_data['aprendizajes']:
							aprendizaje = Aprendizaje.objects.get(resultado=aprendizaje)
							contrato.aprendizajes.add(aprendizaje)
					except:
						return HttpResponseRedirect('/error/12/')

					Alumno.objects.filter(id=form.cleaned_data['alumno'].id).update(docente=form.cleaned_data['docente'], laboral=form.cleaned_data['laboral'])

				return HttpResponseRedirect('/verContratos/')
		else:
			compruebaCurso(request)
			ultimocurso = Curso.objects.all().order_by("-id")[0]
			alumnos = alumnosSinContrato(request, ultimocurso)
			form = crearContratoForm()
		return render_to_response("contratos-programas/crearContrato.html", {'form': form, 'empresa': empresa, 'gerentes': gerentes,
									'laborals': laborals, 'curso': Curso.objects.all().order_by("-id")[0], 'docente': request.user, 'alumnos': alumnos}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarContrato(request, idCon):
	if request.user.es_tutorDocente:
		contratoprograma = get_object_or_404(ContratoPrograma, id=int(idCon))
		empresa = contratoprograma.gerente.empresa
		gerentes = empresa.gerente_set.all()
		laborals = Empresa.objects.tutores(empresa.id)
		aprendizajes = contratoprograma.aprendizajes.all()
		ultimocurso = Curso.objects.all().order_by("-id")[0]
		alumnos = alumnosSinContrato(request, ultimocurso)
		alumnos.append(contratoprograma.alumno)
		if contratoprograma.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
		if request.method == 'POST':
			form = updateContratoForm(request.POST)
			if form.is_valid():
				ContratoPrograma.objects.filter(id=form.cleaned_data['idCon']).update(criterios=form.cleaned_data['criterios'],
												actividades=form.cleaned_data['actividades'], periodo=form.cleaned_data['periodo'],
												modalidad=form.cleaned_data['modalidad'], gerente=form.cleaned_data['gerente'],
												laboral=form.cleaned_data['laboral'],)

				for aprendizaje in form.cleaned_data['aprendizajes']:
					aprendizaje = Aprendizaje.objects.get(resultado=aprendizaje)
					if aprendizaje not in contratoprograma.aprendizajes.all():
						contratoprograma.aprendizajes.add(aprendizaje)

				for aprendizaje in contratoprograma.aprendizajes.all():
					if aprendizaje not in form.cleaned_data['aprendizajes']:
						contratoprograma.aprendizajes.remove(aprendizaje)

				return HttpResponseRedirect('/verContratos/'+ str(contratoprograma.gerente.empresa.id) + '/')

		else:
			form = updateContratoForm(initial={'idCon': contratoprograma.id, 'actividades': contratoprograma.actividades,
										'criterios': contratoprograma.criterios, 'aprendizajes': contratoprograma.aprendizajes.all(),
										'periodo': contratoprograma.periodo, 'modalidad': contratoprograma.modalidad,
										'gerente': contratoprograma.gerente, 'laboral': contratoprograma.laboral,})

		return render_to_response('contratos-programas/editarContrato.html', {'form': form, 'contratoprograma': contratoprograma, 'aprendizajes': aprendizajes, 'laborals': laborals, 'gerentes': gerentes, 'empresa': empresa, 'alumnos':alumnos}, context_instance=RequestContext(request))

	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verContratos(request, idEmp=None):
	if request.user.es_tutorDocente:
		if request.method == 'POST':
			pass
		else:
			if idEmp:
				empresa = get_object_or_404(Empresa, id=int(idEmp))
				gerentes = empresa.gerente_set.all()
				contratos = ContratoPrograma.objects.filter(gerente__in=gerentes).order_by("-id")
			else:
				empresa = None
				contratos = ContratoPrograma.objects.filter(docente=request.user).order_by("-id")
		return render_to_response('contratos-programas/verContratos.html', {'contratos': contratos, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verContrato(request, idCont):
	if request.user.es_tutorDocente:
		if request.method == 'POST':
			pass
		else:
			contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
			aprendizajes = contrato.aprendizajes.all()
			return render_to_response('contratos-programas/verContrato.html', {'contrato': contrato, 'aprendizajes': aprendizajes}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')

################### FIN CONTRATO ###################

###################   GERENTE    ###################


@login_required
def crearGerente(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			form = registroGerenteForm(request.POST)
			if form.is_valid():
				try:
					Gerente.objects.create(first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'],
											nif=form.cleaned_data['nif'], empresa=form.cleaned_data['empresa'])
				except IntegrityError:
					return HttpResponseRedirect('/error/3/')

				return HttpResponseRedirect('/verGerentes/'+ str(form.cleaned_data['empresa'].id) + '/')
		else:
			form = registroGerenteForm()

		if idEmp:
			empresa = get_object_or_404(Empresa, id=int(idEmp))
		else:
			empresa = None

		return render_to_response("gerentes/crearGerente.html", {'form': form, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarGerente(request, idGer):
	if request.user.es_tutorDocente or request.user.is_staff:
		gerente = get_object_or_404(Gerente, id=int(idGer))
		if request.method == 'POST':
			form = updateGerenteForm(request.POST)
			if form.is_valid():
				Gerente.objects.filter(id=form.cleaned_data['idGer']).update(nif=form.cleaned_data['nif'],
										first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'])
			return HttpResponseRedirect('/verGerentes/'+ str(gerente.empresa.id) + '/')
		else:
			form = updateGerenteForm(initial={'idGer': gerente.id, 'nif': gerente.nif,
										'first_name': gerente.first_name, 'last_name': gerente.last_name})
		return render_to_response('gerentes/editarGerente.html', {'form': form, 'gerente': gerente}, context_instance=RequestContext(request))

	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verGerentes(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			if idEmp:
				empresa = get_object_or_404(Empresa, id=int(idEmp))
				gerentes = empresa.gerente_set.all()
			else:
				empresa = None
				gerentes = Gerente.objects.filter()
		return render_to_response('gerentes/verGerentes.html', {'gerentes': gerentes, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')

################### FIN GERENTE ###################


################### CENTROS ###################


@login_required
def crearCentro(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			form = registroCentroForm(request.POST)
			if form.is_valid():
				try:
					Centro.objects.create(direccion=form.cleaned_data['direccion'], telefono=form.cleaned_data['telefono'],
											fax=form.cleaned_data['fax'],  poblacion=form.cleaned_data['poblacion'],
											email=form.cleaned_data['email'],  postal=form.cleaned_data['postal'], empresa=form.cleaned_data['empresa'])
				except:
					return HttpResponseRedirect('/error/0/')

				return HttpResponseRedirect('/verCentros/'+ str(form.cleaned_data['empresa'].id) + '/')
		else:
			form = registroCentroForm()

		if idEmp:
			empresa = get_object_or_404(Empresa, id=int(idEmp))
		else:
			empresa = None
		return render_to_response("centros/crearCentro.html", {'form': form, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarCentro(request, idCen):
	if request.user.es_tutorDocente or request.user.is_staff:
		centro = get_object_or_404(Centro, id=int(idCen))
		if request.method == 'POST':
			form = updateCentroForm(request.POST)
			if form.is_valid():
				Centro.objects.filter(id=form.cleaned_data['idCen']).update(direccion=form.cleaned_data['direccion'],
										telefono=form.cleaned_data['telefono'], fax=form.cleaned_data['fax'],
										poblacion=form.cleaned_data['poblacion'], email=form.cleaned_data['email'],
										postal=form.cleaned_data['postal'])
			return HttpResponseRedirect('/verCentros/'+ str(centro.empresa.id) + '/')
		else:
			form = updateCentroForm(initial={'idCen': centro.id, 'direccion': centro.direccion,
									'telefono': centro.telefono, 'fax': centro.fax, 'poblacion': centro.poblacion,
									'email': centro.email, 'postal': centro.postal})
		return render_to_response('centros/editarCentro.html', {'form': form, 'centro': centro}, context_instance=RequestContext(request))

	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verCentros(request, idEmp=None):
	if request.user.es_tutorDocente or request.user.is_staff:
		if request.method == 'POST':
			pass
		else:
			if idEmp:
				empresa = get_object_or_404(Empresa, id=int(idEmp))
				centros = empresa.centro_set.all()
			else:
				empresa = None
				centros = Centro.objects.filter()
		return render_to_response('centros/verCentros.html', {'centros': centros, 'empresa': empresa}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


################### FIN CENTROS ###################

################### VISITAS ###################


@login_required
def crearVisita(request, idCont):
	if request.user.es_tutorDocente:
		contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
		if contrato.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')

		aprendizajes = contrato.aprendizajes.all()
		if request.method == 'POST':
			form = VisitaForm(request.POST)
			if form.is_valid():
				visitas = Visita.objects.filter(fecha=form.cleaned_data['fecha'], contratoprograma=form.cleaned_data['contratoprograma']).count()
				if visitas > 0:
					return HttpResponseRedirect('/error/8/')
				else:
					visita = Visita.objects.create(fecha=form.cleaned_data['fecha'], contratoprograma=form.cleaned_data['contratoprograma'],
													otro_motivo=form.cleaned_data['otro_motivo'],  tiempo=form.cleaned_data['tiempo'],
													modalidad=form.cleaned_data['modalidad'])

				aprendizajes = form.cleaned_data['aprendizajesPositivos']
				for aprendizaje in aprendizajes:
					aprendizaje = Aprendizaje.objects.get(resultado=aprendizaje)
					visita.aprendizajesPositivos.add(aprendizaje)

				return HttpResponseRedirect('/verVisitasAlu/'+ str(contrato.alumno.id) + '/')

		else:
			form = VisitaForm()

		return render_to_response("visitas/crearVisita.html", {'form': form, 'contrato': contrato, 'aprendizajes': aprendizajes}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def editarVisita(request, idVis):
	if request.user.es_tutorDocente:
		visita = get_object_or_404(Visita, id=int(idVis))
		aprendizajes = visita.contratoprograma.aprendizajes.all()
		if visita.contratoprograma.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
		if request.method == 'POST':
			form = VisitaForm(request.POST)
			if form.is_valid():
				Visita.objects.filter(id=form.cleaned_data['idVis']).update(fecha=form.cleaned_data['fecha'],
												otro_motivo=form.cleaned_data['otro_motivo'], tiempo=form.cleaned_data['tiempo'],
												modalidad=form.cleaned_data['modalidad'])

				for aprendizaje in form.cleaned_data['aprendizajesPositivos']:
					aprendizaje = Aprendizaje.objects.get(resultado=aprendizaje)
					if aprendizaje not in visita.aprendizajesPositivos.all():
						visita.aprendizajesPositivos.add(aprendizaje)

				for aprendizaje in visita.aprendizajesPositivos.all():
					if aprendizaje not in form.cleaned_data['aprendizajesPositivos']:
						visita.aprendizajesPositivos.remove(aprendizaje)

				return HttpResponseRedirect('/verVisitasAlu/'+ str(visita.contratoprograma.alumno.id) + '/')

		else:
			form = VisitaForm(initial={'idVis': visita.id, 'fecha': visita.fecha, 'contrato': visita.contratoprograma,
										'aprendizajesPositivos': visita.aprendizajesPositivos.all(), 'otro_motivo': visita.otro_motivo,
										'tiempo': visita.tiempo, 'modalidad': visita.modalidad})

		return render_to_response('visitas/editarVisita.html', {'form': form, 'contrato': visita.contratoprograma, 'aprendizajes': aprendizajes}, context_instance=RequestContext(request))

	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def crearVisitaAlu(request, idAlu):
	if request.user.es_tutorDocente:
		if request.method == 'POST':
			pass
		else:
			alumno = get_object_or_404(Alumno, id=int(idAlu))
			contratos = ContratoPrograma.objects.filter(alumno=alumno, docente=request.user).order_by("-curso")
			if not contratos:
				return HttpResponseRedirect('/error/13/')

			ultimocontrato = contratos[0]
			if ultimocontrato.docente.id != request.user.id:
				return HttpResponseRedirect('/error/13/')

		return HttpResponseRedirect('/crearVisita/' + str(ultimocontrato.id) + '/')
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verVisitas(request, idCont=None):
	if request.user.es_tutorDocente:
		if request.method == 'POST':
			pass
		else:
			if idCont:
				contrato = get_object_or_404(ContratoPrograma, id=int(idCont))
				visitas = contrato.visita_set.all().order_by("-fecha")
			else:
				contrato = None
				visitas = Visita.objects.filter().order_by("-fecha")
		return render_to_response('visitas/verVisitas.html', {'contrato': contrato, 'visitas': visitas}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def verVisitasAlu(request, idAlu):
	alumno = get_object_or_404(Alumno, id=int(idAlu))

	if request.user.es_tutorDocente:
		if alumno.docente == None:
			return HttpResponseRedirect('/error/13/')
		elif alumno.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
	elif request.user.es_tutorLaboral:
		if alumno.laboral == None:
			return HttpResponseRedirect('/error/13/')
		if alumno.laboral.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
	else:
		return HttpResponseRedirect('/error/2/')

	contratos = ContratoPrograma.objects.filter(alumno=alumno).order_by("-curso")
	visitas = Visita.objects.filter(contratoprograma__in=contratos).order_by("-fecha")

	return render_to_response('visitas/verVisitas.html', {'contratos': contratos, 'visitas': visitas, 'alumno': alumno}, context_instance=RequestContext(request))


@login_required
def verVisita(request, idVis):
	if request.user.es_tutorDocente:
		visita = get_object_or_404(Visita, id=int(idVis))
		if visita.contratoprograma.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
		aprendizajesEsperados = visita.contratoprograma.aprendizajes.all()
		aprendizajesPositivos = visita.aprendizajesPositivos.all()
	else:
		return HttpResponseRedirect('/error/2/')

	return render_to_response('visitas/verVisita.html', {'visita': visita, 'aprendizajesEsperados': aprendizajesEsperados, 'aprendizajesPositivos': aprendizajesPositivos}, context_instance=RequestContext(request))


@login_required
def VisitaPdf(request, idVis):
	if request.user.es_tutorDocente:
		if request.method == 'GET':
			visita = get_object_or_404(Visita, id=int(idVis))
			if visita.contratoprograma.docente.id != request.user.id:
				return HttpResponseRedirect('/error/13/')
			aprendizajesEsperados = visita.contratoprograma.aprendizajes.all()
			aprendizajesPositivos = visita.aprendizajesPositivos.all()
			html = render_to_string('visitas/VisitaPdf.html', {'pagesize': 'A4', 'visita': visita, 'aprendizajesEsperados': aprendizajesEsperados, 'aprendizajesPositivos': aprendizajesPositivos}, context_instance=RequestContext(request))
			nombrepdf = 'Visita_' + str(visita.fecha) + '_' + str(visita.contratoprograma.alumno)
			return generar_pdf(html, nombrepdf)
	else:
		return HttpResponseRedirect('/error/2/')


@login_required
def borrarVisita(request, idVis):
	if request.user.es_tutorDocente:
		visita = get_object_or_404(Visita, id=int(idVis))
		if visita.contratoprograma.docente.id != request.user.id:
			return HttpResponseRedirect('/error/13/')
		Idcontratovisita = visita.contratoprograma.id
		visita.delete()
		return HttpResponseRedirect('/verVisitas/' + str(Idcontratovisita) + '/')

	else:
		return HttpResponseRedirect('/error/2/')
