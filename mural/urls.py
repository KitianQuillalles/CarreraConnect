from django.urls import path
from . import views

urlpatterns = [
    # Index público: página de selección por niveles
    path('', views.index, name='index'),
    # Mural público (accedido desde la index o directamente)
    path('mural/', views.mural_principal, name='mural_principal'),
    path('mural/area/<int:area_id>/', views.mural_principal, name='mural_area'),
    path('ir/', views.ir_a_mis_areas, name='ir_mis_areas'),
    # Panel de contenidos (jefe de carrera / admin)
    path('panel/contenidos/', views.contenidos_mis_areas, name='contenidos_mis_areas'),
    path('panel/contenidos/nuevo/', views.contenido_crear, name='contenido_crear'),
    path('panel/contenidos/<int:pk>/editar/', views.contenido_editar, name='contenido_editar'),
    path('panel/contenidos/<int:pk>/eliminar/', views.contenido_eliminar, name='contenido_eliminar'),
]
