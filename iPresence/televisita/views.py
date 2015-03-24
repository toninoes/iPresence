# -*- coding: utf-8 -*-

import OpenTokSDK
from misitio.presence.models import Alumno
from misitio.televisita.forms import AutorizadoForm
from misitio.televisita.models import Room
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from misitio.Pubnub import Pubnub
from django.conf import settings


PUBNUB_PUBLISH_KEY = '-----'
PUBNUB_SUBSCRIBE_KEY = '----'
PUBNUB_SECRET_KEY = '----'

API_KEY = '----'
API_SECRET = '----'
API_JS_FLASH = 'https://swww.tokbox.com/v1.1/js/TB.min.js'
API_JS_WEBRTC = 'https://swww.tokbox.com/webrtc/v2.0/js/TB.min.js'


@login_required
def error(request, num):
	error = {
		'2': 'No perteneces al grupo de Docentes',
		'5': 'Ha ocurrido un error en el envío del correo electrónico',
		'7': 'No estas autorizado a realizar videoconferencias',
	}
	return render_to_response('error.html', {'error': error[num]}, context_instance=RequestContext(request))


@login_required
def dameIP(request):
	return request.META['REMOTE_ADDR']


@login_required
def obtenerSalaId(request):
	opentok_sdk = OpenTokSDK.OpenTokSDK(API_KEY, API_SECRET)
	session_address = dameIP(request)
	session = opentok_sdk.create_session(session_address)
	return session.session_id


@login_required
def obtenerToken(request, sessionId):
	opentok_sdk = OpenTokSDK.OpenTokSDK(API_KEY, API_SECRET)
	role_constants = OpenTokSDK.RoleConstants
	token = opentok_sdk.generate_token(sessionId, role_constants.PUBLISHER)
	return token


@login_required
def misAlumnosId(request, yoTambien=False):
	alumnos = Alumno.objects.filter(laboral=request.user)
	listaIdAlumnos = []
	for alumno in alumnos:
		listaIdAlumnos.append(alumno.id)
	if yoTambien:
		listaIdAlumnos.append(request.user.id)
	return listaIdAlumnos


@login_required
def enviarInvitacion(request, dicc):
	asunto = render_to_string('invitacion_asunto.txt', dicc)
	mensaje = render_to_string('invitacion_mensaje.txt', dicc)
	email = EmailMessage(asunto, mensaje, to=[dicc['invitado'].email])
	email.send()


@login_required
def enviarMensaje(request, dicc):
	if not request.user.is_staff:
		pubnub = Pubnub(PUBNUB_PUBLISH_KEY, PUBNUB_SUBSCRIBE_KEY, PUBNUB_SECRET_KEY, True)
		pubnub.publish({
			'channel': dicc['invitado'].username,
			'message': dicc['room'].owner.get_full_name() + ' te ha invitado a su sala.'
		})


@login_required
def tokbox(request, sessionId):
	tipoSala = 'flash'
	API = API_JS_FLASH
	if request.method == 'POST':
		if request.user.es_tutorDocente:
			form = AutorizadoForm(request.POST)
		else:
			return HttpResponseRedirect('/error/2/')

		if form.is_valid():
			Room.objects.filter(owner=request.user).update(autorizado=form.cleaned_data['autorizado'])
			room = Room.objects.get(owner=request.user)
			dicc = {'invitado': form.cleaned_data['autorizado'],
					'room': room,
					'servidor': settings.SERVER}
			enviarMensaje(request, dicc)
			if form.cleaned_data['enviarMail']:
				try:
					enviarInvitacion(request, dicc)
				except:
					return HttpResponseRedirect('/error/5/')
	else:
		try:
			room = Room.objects.get(salaId=sessionId)
		except:
			room = get_object_or_404(Room, salaIdWebrtc=sessionId)
			API = API_JS_WEBRTC
			tipoSala = 'webrtc'

		form = None
		if request.user.es_tutorDocente:
			if room.autorizado != request.user:
				room = Room.objects.get(owner=request.user)
			form = AutorizadoForm(initial={'autorizado': room.autorizado})
		elif request.user.es_tutorLaboral:
			if room.autorizado.id not in misAlumnosId(request, True):
				return HttpResponseRedirect('/salas/')
		elif request.user.es_Alumno:
			if room.autorizado != request.user:
				return HttpResponseRedirect('/salas/')

	if request.user.puede_hablar:
		if tipoSala == 'flash':
			token = obtenerToken(request, room.salaId)
		else:
			token = obtenerToken(request, room.salaIdWebrtc)
	else:
		return HttpResponseRedirect('/error/7/')

	return render_to_response('tokbox.html', {'tipoSala': tipoSala, 'room': room, 'token': token, 'form': form, 'API': API, 'API_KEY': API_KEY, 'IP': dameIP(request), 'servidor': settings.SERVER}, context_instance=RequestContext(request))


@login_required
def salas(request):
	if request.user.puede_hablar:

		administrador = User.objects.get(id=1)
		try:
			salaEsperaId = Room.objects.get(owner=administrador).salaId
		except:
			salaEsperaId = obtenerSalaId(request)
			Room.objects.create(owner=administrador, nombre="Sala de Espera", salaId=salaEsperaId)

		if not salaEsperaId:
			salaEsperaId = obtenerSalaId(request)
			Room.objects.filter(owner=administrador).update(salaId=salaEsperaId)

		if request.user.es_tutorDocente:
			try:
				myRoom = Room.objects.get(owner=request.user)
			except:
				MisalaId = obtenerSalaId(request)
				MisalaIdWebrtc = obtenerSalaId(request)
				myRoom = Room.objects.create(owner=request.user, nombre=request.user.get_full_name(), salaId=MisalaId, salaIdWebrtc=MisalaIdWebrtc, autorizado=request.user)

			if not myRoom.salaId:
				MisalaId = obtenerSalaId(request)
				Room.objects.filter(owner=request.user).update(salaId=MisalaId)

			if not myRoom.salaIdWebrtc:
				MisalaIdWebrtc = obtenerSalaId(request)
				Room.objects.filter(owner=request.user).update(salaIdWebrtc=MisalaIdWebrtc)

		else:
			myRoom = None

		token = obtenerToken(request, salaEsperaId)
		if request.user.es_tutorDocente or request.user.es_Alumno:
			Rooms = Room.objects.filter(autorizado=request.user).exclude(owner=request.user)
		elif request.user.es_tutorLaboral:
			Rooms = Room.objects.filter(autorizado__in=misAlumnosId(request, True))
		elif request.user.is_staff:
			Rooms = Room.objects.all().exclude(owner=request.user)
		return render_to_response('salas.html', {'salaEsperaId': salaEsperaId, 'myRoom': myRoom, 'token': token, 'Rooms': Rooms, 'API': API_JS_FLASH, 'API_KEY': API_KEY, 'servidor': settings.SERVER}, context_instance=RequestContext(request))
	else:
		return HttpResponseRedirect('/error/7/')
