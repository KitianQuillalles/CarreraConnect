# mural/urls.py
from django.urls import path, re_path
from . import views

urlpatterns = [
    # ---- 1. APIS PARA REACT ----
    path('api/areas/', views.api_areas, name='api_areas'),
    path('api/contenidos/<int:area_id>/', views.api_contenidos, name='api_contenidos'),

    # ---- 2. PANEL DE ADMINISTRADOR (Intacto) ----
    path('ir/', views.ir_a_mis_areas, name='ir_mis_areas'),
    path('panel/contenidos/', views.contenidos_mis_areas, name='contenidos_mis_areas'),
    path('panel/contenidos/nuevo/', views.contenido_crear, name='contenido_crear'),
    path('panel/contenidos/<int:pk>/editar/', views.contenido_editar, name='contenido_editar'),
    path('panel/contenidos/<int:pk>/eliminar/', views.contenido_eliminar, name='contenido_eliminar'),

    # ---- 3. VISTA ATRAPA-TODO PARA REACT ----
    # El index principal
    path('', views.vista_react, name='index'),
    # Las subrutas de React Router (ej: /mural/5/)
    re_path(r'^mural/.*$', views.vista_react, name='mural_react'),
]