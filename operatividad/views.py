import logging

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import requires_csrf_token
from django.contrib import messages

from .forms import PerfilForm, CrearUsuarioForm
from .models import AsignacionArea
from mural.models import Area

User = get_user_model()

logger = logging.getLogger(__name__)


@requires_csrf_token
def fallo_csrf(request, reason=""):
    """Vista personalizada para manejar errores de CSRF.

    Registra el incidente y muestra una plantilla amigable.
    """
    try:
        logger.warning('CSRF failure for path %s, user=%s, reason=%s', request.path, getattr(request, 'user', None), reason)
    except Exception:
        logger.exception('Error registrando fallo CSRF')

    contexto = {
        'reason': reason,
        'user_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
    }
    return render(request, 'operatividad/csrf_failure.html', contexto, status=403)


def iniciar_sesion(request):
    """Iniciar sesión (acepta campos legacy y modernos)."""
    if request.method == 'POST':
        password = request.POST.get('password') or request.POST.get('password1')
        email = request.POST.get('email') or request.POST.get('username') or ''
        user = authenticate(request, username=email, password=password) if email else None
        if user is not None:
            login(request, user)
            siguiente = request.POST.get('next') or request.GET.get('next')
            if siguiente:
                return redirect(siguiente)
            return redirect('panel_operatividad')
        messages.error(request, 'Credenciales inválidas')
    return render(request, 'operatividad/login.html')


@login_required
def cerrar_sesion(request):
    logout(request)
    return redirect('login')


@login_required
def panel_operatividad(request):
    return render(request, 'operatividad/panel_operatividad.html')


@login_required
def listar_cuentas(request):
    cuentas = User.objects.all()
    return render(request, 'operatividad/cuentas_list.html', {'cuentas': cuentas})


@login_required
def crear_cuenta(request):
    messages.info(request, 'La creación de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')


@login_required
def actualizar_cuenta(request, pk):
    messages.info(request, 'La edición de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')


@login_required
def eliminar_cuenta(request, pk):
    messages.info(request, 'La eliminación de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')


@login_required
def gestionar_usuarios(request):
    try:
        qs = request.META.get('QUERY_STRING', '')
        base = reverse('contenidos_mis_areas')
        if qs:
            return HttpResponseRedirect(f"{base}?{qs}")
        return redirect('contenidos_mis_areas')
    except Exception:
        logger.exception('Error redirigiendo en gestionar_usuarios')
        return redirect('contenidos_mis_areas')


@login_required
def crear_usuario(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        try:
            if request.user.is_superuser or request.user.is_staff:
                form.fields['area'].queryset = Area.objects.all()
            else:
                jefe_area_ids = AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True)
                form.fields['area'].queryset = Area.objects.filter(pk__in=list(jefe_area_ids)).distinct()
        except Exception:
            logger.exception('Error preparando queryset de áreas en crear_usuario')
        if form.is_valid():
            data = form.cleaned_data
            new = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password1'],
            )
            requested_role = (request.POST.get('role') or '').strip()
            if not (request.user.is_superuser or request.user.is_staff):
                requested_role = AsignacionArea.ROL_EDITOR
            areas_sel = data.get('area') or []
            try:
                from mural.models import Asignacion
                if not (request.user.is_superuser or request.user.is_staff):
                    allowed_ids = list(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                    areas_sel = [a for a in areas_sel if a.id in allowed_ids]
                for a in areas_sel:
                    asign, _ = Asignacion.objects.get_or_create(area=a, usuario=new)
                    try:
                        asign.rol = requested_role or asign.rol or AsignacionArea.ROL_EDITOR
                        asign.save(update_fields=['rol'])
                    except Exception:
                        logger.exception('Error guardando asignación para nuevo usuario')
            except Exception:
                logger.exception('Error procesando asignaciones para nuevo usuario')
            messages.success(request, 'Usuario creado')
            return redirect('gest_usuarios')
        else:
            try:
                for field, errs in form.errors.items():
                    for e in errs:
                        messages.error(request, f"{field}: {e}")
            except Exception:
                messages.error(request, 'Error de validación en el formulario de usuario.')
            try:
                if not (request.user.is_superuser or request.user.is_staff):
                    jefe_area_ids = set(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                    posted_area_ids = set([int(x) for x in request.POST.getlist('area') if x])
                    if posted_area_ids and not posted_area_ids.intersection(jefe_area_ids):
                        messages.error(request, 'No posee permisos para asignar las áreas seleccionadas.')
            except Exception:
                logger.exception('Error verificando permisos de asignación de áreas en crear_usuario')
            return redirect('gest_usuarios')
    return redirect('gest_usuarios')


@login_required
def mi_perfil(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado')
            return HttpResponseRedirect(reverse('gest_usuarios') + '?section=perfil')
    return HttpResponseRedirect(reverse('gest_usuarios') + '?section=perfil')


@login_required
def editar_usuario(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre') or request.POST.get('first_name')
        apellidos = request.POST.get('apellidos') or request.POST.get('last_name')
        correo = request.POST.get('correo') or request.POST.get('email')
        area_ids = request.POST.getlist('area')
        password = request.POST.get('password') or request.POST.get('password1')
        password_confirm = request.POST.get('password2') or request.POST.get('password_confirm')
        if (password or password_confirm):
            if not password:
                messages.error(request, 'Debe proporcionar la nueva contraseña.')
                return redirect(reverse('gest_usuarios') + '?section=perfil')
            if password != (password_confirm or ''):
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect(reverse('gest_usuarios') + '?section=perfil')
        if nombre is not None:
            user.first_name = (nombre or '').strip()
        if apellidos is not None:
            user.last_name = (apellidos or '').strip()
        if correo:
            correo = correo.strip()
            user.email = correo
            try:
                user.username = correo
            except Exception:
                logger.exception('Error actualizando username al guardar correo')
        user.save()
        try:
            from mural.models import Asignacion
            if area_ids:
                selected_ids = [int(x) for x in area_ids if x]
            else:
                selected_ids = []
            if not (request.user.is_superuser or request.user.is_staff):
                allowed_ids = list(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                selected_ids = [sid for sid in selected_ids if sid in allowed_ids]
            Asignacion.objects.filter(usuario=user).exclude(area__pk__in=selected_ids).delete()
            for aid in selected_ids:
                try:
                    a = Area.objects.get(pk=aid)
                    asign, _ = Asignacion.objects.get_or_create(area=a, usuario=user)
                    try:
                        sent_role = request.POST.get('role') or ''
                        if not (request.user.is_superuser or request.user.is_staff):
                            sent_role = AsignacionArea.ROL_EDITOR
                        if sent_role:
                            asign.rol = sent_role
                            asign.save(update_fields=['rol'])
                    except Exception:
                        pass
                except Area.DoesNotExist:
                    continue
        except Exception:
            logger.exception('Error actualizando asignaciones en editar_usuario')
        if password:
            user.set_password(password)
            user.save()
        messages.success(request, 'Usuario actualizado')
        return redirect('gest_usuarios')
    return redirect('gest_usuarios')


@login_required
def eliminar_usuario(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if request.user == user_obj:
            messages.error(request, 'No puede eliminar su propia cuenta desde aquí.')
            return redirect('gest_usuarios')
        try:
            user_obj.delete()
            messages.success(request, 'Usuario eliminado correctamente.')
        except Exception:
            messages.error(request, 'Error al eliminar el usuario.')
        return redirect('gest_usuarios')
    return redirect('gest_usuarios')


@login_required
def asignar_area_usuario(request, area_id):
    try:
        area = Area.objects.get(pk=area_id)
    except Area.DoesNotExist:
        messages.error(request, 'Área no encontrada')
        return redirect('gest_usuarios')
    if request.method == 'POST':
        user_id = request.POST.get('usuario')
        try:
            from mural.models import Asignacion
            Asignacion.objects.filter(area=area).update(es_responsable=False)
            if user_id:
                u = User.objects.get(pk=int(user_id))
                asign, _ = Asignacion.objects.get_or_create(area=area, usuario=u)
                asign.es_responsable = True
                asign.save(update_fields=['es_responsable'])
                area.usuario = u
                area.save(update_fields=['usuario'])
                messages.success(request, f'Área "{area.nombre}" asignada a {u.get_full_name()}')
            else:
                area.usuario = None
                area.save(update_fields=['usuario'])
                messages.success(request, f'Área "{area.nombre}" desasignada')
        except Exception:
            messages.error(request, 'Usuario no válido o error al asignar')
    return redirect('gest_usuarios')


# Aliases para compatibilidad con nombres antiguos usados en URLs/imports
login_view = iniciar_sesion
logout_view = cerrar_sesion
cuentas_list = listar_cuentas
cuentas_create = crear_cuenta
cuentas_update = actualizar_cuenta
cuentas_delete = eliminar_cuenta
gest_usuarios = gestionar_usuarios
usuarios_crear = crear_usuario
usuarios_mi_perfil = mi_perfil
usuarios_editar = editar_usuario
usuarios_eliminar = eliminar_usuario
usuarios_asignar_area = asignar_area_usuario
csrf_failure = fallo_csrf
