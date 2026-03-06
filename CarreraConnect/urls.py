"""
Configuración de URLs para el proyecto CarreraConnect.

La lista `urlpatterns` enruta las URLs a las vistas. Para más información, consulta:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Ejemplos:
Vistas basadas en funciones
    1. Añade una importación:  from my_app import views
    2. Añade una URL a urlpatterns:  path('', views.home, name='home')
Vistas basadas en clases
    1. Añade una importación:  from other_app.views import Home
    2. Añade una URL a urlpatterns:  path('', Home.as_view(), name='home')
Incluyendo otro URLconf
    1. Importa la función include(): from django.urls import include, path
    2. Añade una URL a urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("mural.urls")),
    path("operatividad/", include("operatividad.urls")),
    # Redirigir raíz /login/ a la ruta real en la app operatividad
    path("login/", RedirectView.as_view(url='/operatividad/login/', permanent=False), name='login'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve the existing project-level `mural_archivos` directory during development
    # so requests to /mural_archivos/<file> work without moving files.
    urlpatterns += [
        re_path(r'^mural_archivos/(?P<path>.*)$', serve, {'document_root': str(settings.BASE_DIR / 'mural_archivos')}),
    ]


