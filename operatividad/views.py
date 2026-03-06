from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from .forms import PerfilForm, CrearUsuarioForm
from mural.models import Area
from .models import AsignacionArea
from django.urls import reverse
from django.http import HttpResponseRedirect
# Note: `render` and `messages` already imported above; avoid duplicates
from django.db.models import Q
from django.views.decorators.csrf import requires_csrf_token
import logging

logger = logging.getLogger(__name__)

def login_view(request):
    if request.method == 'POST':
        # Login por correo electrónico (correo_institucional)
        # accept either 'password' (legacy) or 'password1' (form naming) from POST
        password = request.POST.get('password') or request.POST.get('password1')
        email = request.POST.get('email') or request.POST.get('username') or ''

        user = None
        if email:
            user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            # respetar parámetro 'next' (POST o GET)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('panel_operatividad')   # panel principal por defecto
        else:
            messages.error(request, 'Credenciales inválidas')
    # renderizar la plantilla de login específica de la app operatividad
    return render(request, 'operatividad/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def panel_operatividad(request):
    return render(request, 'operatividad/panel_operatividad.html')

@login_required
def cuentas_list(request):
    cuentas = User.objects.all()
    return render(request, 'operatividad/cuentas_list.html', {'cuentas': cuentas})

@login_required
def cuentas_create(request):
    # Legacy endpoint: la gestión principal de usuarios ahora se realiza
    # desde el panel `gest_contenidos.html` (vista `contenidos_mis_areas`).
    # Para mantener compatibilidad, redirigimos y mostramos un mensaje.
    messages.info(request, 'La creación de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')

@login_required
def cuentas_update(request, pk):
    # Legacy: redirigir a la gestión centralizada
    messages.info(request, 'La edición de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')

@login_required
def cuentas_delete(request, pk):
    # Legacy: redirigir a la gestión centralizada
    messages.info(request, 'La eliminación de cuentas se gestiona desde el panel de contenidos.')
    return redirect('gest_usuarios')


@login_required
def gest_usuarios(request):
    # Ahora la gestión de usuarios se integra directamente en el panel de contenidos.
    # Redirigimos para usar `gest_contenidos.html` y la vista `contenidos_mis_areas`.
    # Preservar parámetros GET para permitir enlaces como
    # /operatividad/usuarios/?section=crear o ?section=perfil
    try:
        qs = request.META.get('QUERY_STRING', '')
        base = reverse('contenidos_mis_areas')
        if qs:
            return HttpResponseRedirect(f"{base}?{qs}")
        return redirect('contenidos_mis_areas')
    except Exception:
        # En caso de error, hacer una redirección segura sin querystring
        return redirect('contenidos_mis_areas')


@login_required
def usuarios_crear(request):
    if request.method == 'POST':
        # limitar queryset de áreas según permisos del usuario que crea
        form = CrearUsuarioForm(request.POST)
        try:
            if request.user.is_superuser or request.user.is_staff:
                form.fields['area'].queryset = Area.objects.all()
            else:
                # si no es superuser/staff, limitar a áreas donde es jefe de área
                jefe_area_ids = AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True)
                form.fields['area'].queryset = Area.objects.filter(pk__in=list(jefe_area_ids)).distinct()
        except Exception:
            pass
        if form.is_valid():
            data = form.cleaned_data
            new = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password1'],
            )
            # determinar rol solicitado pero aplicar restricciones según quien crea
            requested_role = (request.POST.get('role') or '').strip()
            if not (request.user.is_superuser or request.user.is_staff):
                # si es jefe de área, forzar rol Editor
                requested_role = AsignacionArea.ROL_EDITOR
            areas_sel = data.get('area') or []
            try:
                from mural.models import Asignacion
                # si el creador no es admin, limitar áreas a las que el creador puede asignar
                if not (request.user.is_superuser or request.user.is_staff):
                    allowed_ids = list(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                    areas_sel = [a for a in areas_sel if a.id in allowed_ids]
                for a in areas_sel:
                    asign, _ = Asignacion.objects.get_or_create(area=a, usuario=new)
                    try:
                        asign.rol = requested_role or asign.rol or AsignacionArea.ROL_EDITOR
                        asign.save(update_fields=['rol'])
                    except Exception:
                        pass
            except Exception:
                pass
            messages.success(request, 'Usuario creado')
            return redirect('gest_usuarios')
        else:
            # Mostrar errores de validación como notificaciones para el usuario
            try:
                for field, errs in form.errors.items():
                    for e in errs:
                        messages.error(request, f"{field}: {e}")
            except Exception:
                messages.error(request, 'Error de validación en el formulario de usuario.')
            # Si el usuario es Jefe de área y envió áreas fuera de su ámbito, informar
            try:
                if not (request.user.is_superuser or request.user.is_staff):
                    jefe_area_ids = set(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                    posted_area_ids = set([int(x) for x in request.POST.getlist('area') if x])
                    if posted_area_ids and not posted_area_ids.intersection(jefe_area_ids):
                        messages.error(request, 'No posee permisos para asignar las áreas seleccionadas.')
            except Exception:
                pass
            return redirect('gest_usuarios')
    return redirect('gest_usuarios')


@login_required
def usuarios_mi_perfil(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado')
            return HttpResponseRedirect(reverse('gest_usuarios') + '?section=perfil')
    return HttpResponseRedirect(reverse('gest_usuarios') + '?section=perfil')


@login_required
def usuarios_editar(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        # aceptar tanto nombres de campo legacy en español como los usados
        # por la plantilla (`first_name`, `last_name`, `email`). Esto evita
        # que el servidor ignore cambios cuando la plantilla envía otros nombres.
        nombre = request.POST.get('nombre') or request.POST.get('first_name')
        apellidos = request.POST.get('apellidos') or request.POST.get('last_name')
        correo = request.POST.get('correo') or request.POST.get('email')
        # permitir múltiples áreas (select multiple)
        area_ids = request.POST.getlist('area')
        # accept either legacy 'password' or form-style 'password1'
        password = request.POST.get('password') or request.POST.get('password1')
        # confirmation may come as 'password2' or 'password_confirm'
        password_confirm = request.POST.get('password2') or request.POST.get('password_confirm')

        # If a password change was submitted, validate confirmation server-side
        if (password or password_confirm):
            if not password:
                messages.error(request, 'Debe proporcionar la nueva contraseña.')
                return redirect(reverse('gest_usuarios') + '?section=perfil')
            if password != (password_confirm or ''):
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect(reverse('gest_usuarios') + '?section=perfil')


        # Aplicar cambios simples; usar strip() para normalizar entradas
        if nombre is not None:
            user.first_name = (nombre or '').strip()
        if apellidos is not None:
            user.last_name = (apellidos or '').strip()
        if correo:
            correo = correo.strip()
            user.email = correo
            # Mantener username sincronizado con email para compatibilidad
            try:
                user.username = correo
            except Exception:
                pass

        # Nota: la gestión de roles ahora se realiza mediante Asignacion/AsignacionArea.
        # Si la aplicación necesita asignar roles permanentes por usuario, adaptar aquí.
        user.save()
        # asignar áreas seleccionadas (crear/actualizar Asignacion y marcar responsable)
        try:
            from mural.models import Asignacion
            if area_ids:
                selected_ids = [int(x) for x in area_ids if x]
            else:
                selected_ids = []
            # eliminar asignaciones previas que no están en la nueva lista
            # Si el editor no es superuser/staff, limitar selected_ids a áreas que puede gestionar
            if not (request.user.is_superuser or request.user.is_staff):
                allowed_ids = list(AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).values_list('area_id', flat=True))
                selected_ids = [sid for sid in selected_ids if sid in allowed_ids]

            Asignacion.objects.filter(usuario=user).exclude(area__pk__in=selected_ids).delete()
            for aid in selected_ids:
                try:
                    a = Area.objects.get(pk=aid)
                    asign, _ = Asignacion.objects.get_or_create(area=a, usuario=user)
                    # aplicar rol si se envió (respeta restricciones)
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
            pass

        # contraseña opcional
        if password:
            user.set_password(password)
            user.save()

        messages.success(request, 'Usuario actualizado')
        return redirect('gest_usuarios')

    return redirect('gest_usuarios')


@login_required
def usuarios_eliminar(request, pk):
    # Eliminar usuario desde la interfaz centralizada sin depender de cuentas_*.
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        # prevenir que un usuario elimine a sí mismo accidentalmente
        if request.user == user_obj:
            messages.error(request, 'No puede eliminar su propia cuenta desde aquí.')
            return redirect('gest_usuarios')
        try:
            user_obj.delete()
            messages.success(request, 'Usuario eliminado correctamente.')
        except Exception:
            messages.error(request, 'Error al eliminar el usuario.')
        return redirect('gest_usuarios')
    # si no es POST, redirigir al panel (la confirmación se maneja en la UI)
    return redirect('gest_usuarios')


@login_required
def usuarios_asignar_area(request, area_id):
    """Asignar/desasignar un usuario responsable a un área (POST).

    POST params: 'usuario' puede ser vacío (desasignar) o id de usuario.
    """
    try:
        area = Area.objects.get(pk=area_id)
    except Area.DoesNotExist:
        messages.error(request, 'Área no encontrada')
        return redirect('gest_usuarios')

    if request.method == 'POST':
        user_id = request.POST.get('usuario')
        # Comportamiento: usar Asignacion.es_responsable como fuente de verdad.
        try:
            # desmarcar responsables previos para esta área
            from mural.models import Asignacion
            Asignacion.objects.filter(area=area).update(es_responsable=False)
            if user_id:
                u = User.objects.get(pk=int(user_id))
                # asegurar la asignación y marcar responsable
                asign, _ = Asignacion.objects.get_or_create(area=area, usuario=u)
                asign.es_responsable = True
                asign.save(update_fields=['es_responsable'])
                # Mantener compatibilidad: actualizar también Area.usuario
                area.usuario = u
                area.save(update_fields=['usuario'])
                messages.success(request, f'Área "{area.nombre}" asignada a {u.get_full_name()}')
            else:
                # sin usuario: dejar sin responsable
                area.usuario = None
                area.save(update_fields=['usuario'])
                messages.success(request, f'Área "{area.nombre}" desasignada')
        except Exception:
            messages.error(request, 'Usuario no válido o error al asignar')

    return redirect('gest_usuarios')


@requires_csrf_token
def csrf_failure(request, reason=""):
    """Vista personalizada para manejar errores de CSRF.

    Muestra un mensaje amigable al usuario y sugiere acciones de recuperación.
    """
    try:
        # registrar para auditoría
        logger.warning('CSRF failure for path %s, user=%s, reason=%s', request.path, getattr(request, 'user', None), reason)
    except Exception:
        pass

    # Si no está autenticado, sugerir login; si está autenticado, sugerir recargar/volver.
    contexto = {
        'reason': reason,
        'user_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
    }
    return render(request, 'operatividad/csrf_failure.html', contexto, status=403)
