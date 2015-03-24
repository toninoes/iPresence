from django.conf.urls.defaults import patterns
from views import *


urlpatterns = patterns('',
	(r'^error/(\d+)/$', error),
	(r'^tokbox/(\S+)?/?$', tokbox),
	(r'^salas/$', salas),
)
