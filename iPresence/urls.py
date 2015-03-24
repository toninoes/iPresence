from django.conf.urls.defaults import patterns, include, url
from misitio.presence.views import *


# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	(r'^admin/doc/', include('django.contrib.admindocs.urls')),####
	(r'^admin/jsi18n/$', 'django.views.i18n.javascript_catalog'),####
	#(r'^admin/(.*)', admin.site.root),	####
	url(r'^', include('misitio.presence.urls')),
	url(r'^', include('misitio.televisita.urls')),
	url(r'^admin/', include(admin.site.urls)),
)
