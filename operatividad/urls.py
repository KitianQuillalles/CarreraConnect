# operatividad/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Autenticación operatividad
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('usuarios/', views.gest_usuarios, name='gest_usuarios'),
    path('usuarios/crear/', views.usuarios_crear, name='usuarios_crear'),
    path('usuarios/mi-perfil/', views.usuarios_mi_perfil, name='usuarios_mi_perfil'),
    path('usuarios/<int:pk>/editar/', views.usuarios_editar, name='usuarios_editar'),
    path('usuarios/<int:pk>/eliminar/', views.usuarios_eliminar, name='usuarios_eliminar'),
    path('usuarios/areas/<int:area_id>/asignar/', views.usuarios_asignar_area, name='usuarios_asignar_area'),

    # Panel principal
    path('panel/', views.panel_operatividad, name='panel_operatividad'),

    # Gestión de cuentas de usuario
    path('panel/cuentas/', views.cuentas_list, name='cuentas_list'),
    path('panel/cuentas/nueva/', views.cuentas_create, name='cuentas_create'),
    path('panel/cuentas/<int:pk>/editar/', views.cuentas_update, name='cuentas_update'),
    path('panel/cuentas/<int:pk>/eliminar/', views.cuentas_delete, name='cuentas_delete'),
]
