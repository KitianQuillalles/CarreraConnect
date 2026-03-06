"""Vistas del módulo `mural`.

Se consolidó la implementación aquí; asegurar que no haya referencias
circulares a `views_new`.
"""
from collections import OrderedDict
import unicodedata

from django.contrib import messages
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
import datetime
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Min
from django.conf import settings
from django.core.exceptions import ValidationError

from operatividad.models import Area, Contenido, Archivo as ArchivoModel, AreaDestinatario, AsignacionArea
from django.contrib.auth import get_user_model
from .forms import ContenidoForm
from django import forms as django_forms

logger = logging.getLogger(__name__)


def _group_areas_by_categoria():
	# Agrupar por nivel_formacion: queremos secciones separadas para U, IP, CFT y GEN
	nivel_labels = {
		Area.NIVEL_U: 'Universidad (U)',
		Area.NIVEL_IP: 'Instituto Profesional (IP)',
		Area.NIVEL_CFT: 'Centro de Formación Técnica (CFT)',
		Area.NIVEL_GEN: 'General (GEN)',
	}

	# Mantener orden preferente: U, IP, CFT, GEN
	preferred = [Area.NIVEL_U, Area.NIVEL_IP, Area.NIVEL_CFT, Area.NIVEL_GEN]

	groups = []
	for nivel in preferred:
		areas_qs = Area.objects.filter(nivel_formacion=nivel).order_by('nombre')
		areas_list = list(areas_qs)
		# Para el nivel GEN queremos que el grupo siempre exista (incluso si está vacío)
		if areas_list or nivel == Area.NIVEL_GEN:
			groups.append({'nombre': nivel_labels.get(nivel, nivel), 'areas': areas_list})

	# Agregar cualquier área restante que no tenga nivel asignado o niveles inesperados
	other_areas = Area.objects.exclude(nivel_formacion__in=preferred).order_by('nombre')
	other_list = list(other_areas)
	if other_list:
		groups.append({'nombre': 'Otras áreas', 'areas': other_list})

	if not groups:
		# fallback: mostrar todas agrupadas bajo 'Áreas'
		groups = [{'nombre': 'Áreas', 'areas': list(Area.objects.all().order_by('nombre'))}]

	return groups


def _user_default_area(user, allowed_areas):
	"""Determina el `area_origen` por defecto para `user`.

	Reglas:
	- Si existe un `Area` con `usuario == user`, usarla (responsable).
	- Si existe una `AsignacionArea` para el user con rol 'Jefe de área' o 'Administrador', usar esa área.
	- Si el conjunto `allowed_areas` tiene exactamente 1 elemento, usarlo.
	- En otros casos devolver `None` para que el usuario elija explícitamente.
	"""
	try:
		# 1) Área donde es responsable (Area.usuario)
		resp = Area.objects.filter(usuario=user).first()
		if resp:
			return resp

		# 2) Asignaciones con rol preferente
		if AsignacionArea.objects.filter(usuario=user).exists():
			# Preferir Jefe, luego Administrador, luego cualquier asignación
			jefe = AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_JEFE).select_related('area').first()
			if jefe and jefe.area:
				return jefe.area
			admin = AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_ADMIN).select_related('area').first()
			if admin and admin.area:
				return admin.area
			any_asig = AsignacionArea.objects.filter(usuario=user).select_related('area').first()
			if any_asig and any_asig.area:
				return any_asig.area

		# 2b) Si el usuario está relacionado a algún área GEN, preferir esa área (DAE)
		try:
			gen_area = Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).first()
			if gen_area:
				return gen_area
		except Exception:
			pass

		# 3) Si sólo tiene un allowed_area, usarla
		try:
			if allowed_areas is not None and hasattr(allowed_areas, 'count') and allowed_areas.count() == 1:
				return allowed_areas.first()
		except Exception:
			pass
	except Exception:
		return None
	return None


def _first_area_from_group(group):
	areas = group.get('areas') if group else []
	return areas[0] if areas else None


def _published_contenidos_for_area(area):
	# Mostrar los contenidos que están publicados PARA la área solicitada
	# (no exigir que el contenido haya sido originado en la misma área).
	from django.db.models import Min
	return Contenido.objects.filter(destinatarios__area=area, destinatarios__estado=AreaDestinatario.ESTADO_PUBLICADO).distinct().annotate(min_fecha_limite=Min('destinatarios__fecha_limite')).order_by('-fecha_creacion')


def _published_contenidos_all():
	from django.db.models import Min
	return Contenido.objects.filter(destinatarios__estado=AreaDestinatario.ESTADO_PUBLICADO).distinct().annotate(min_fecha_limite=Min('destinatarios__fecha_limite')).order_by('-fecha_creacion')


def _sync_publication_states():
	"""Promueve EN_ESPERA -> PUBLICADO cuando fecha_asignacion <= now
	y demota PUBLICADO -> EXPIRADO cuando fecha_limite < now.

	Esta función se puede llamar desde views para asegurar que las
	filas en la base reflejen el estado real al momento de la petición.
	Devuelve una tupla (promoted_count, expired_count).
	"""
	try:
		now = timezone.now()
		future = now + datetime.timedelta(days=365 * 100)

		# Promover EN_ESPERA -> PUBLICADO cuando fecha_asignacion <= now
		promote_qs = AreaDestinatario.objects.filter(
			estado=AreaDestinatario.ESTADO_EN_ESPERA,
			fecha_asignacion__lte=now
		)
		promoted = int(promote_qs.count() or 0)
		logger.debug("_sync: now=%s promote_qs_count=%s", now, promoted)
		if promoted:
			# conservar list of contenido ids afectados
			contenido_ids = list(promote_qs.values_list('contenido_id', flat=True))
			promote_qs.update(estado=AreaDestinatario.ESTADO_PUBLICADO)
			logger.debug("_sync: promoted contenido_ids=%s", contenido_ids)
			# No almacenamos `fecha_publicado` en el modelo Contenido; el estado de publicación
			# se representa por filas de AreaDestinatario. Registrar para auditoría.
			try:
				logger.debug("_sync: promoted contents (area-level) ids=%s", list(contenido_ids))
			except Exception:
				pass

		# Demotar PUBLICADO -> BORRADOR cuando fecha_limite < now
		# (una vez expirado, no mantenerlo en EN_ESPERA; tratar como borrador)
		expire_qs = AreaDestinatario.objects.filter(
			fecha_limite__lt=now,
			estado=AreaDestinatario.ESTADO_PUBLICADO
		)
		expired = int(expire_qs.count() or 0)
		logger.debug("_sync: expire_qs_count=%s", expired)
		if expired:
			# Obtener contenidos afectados antes de actualizar
			expired_contenido_ids = list(expire_qs.values_list('contenido_id', flat=True))
			# marcar como BORRADOR y actualizar fecha_asignacion a ahora
			expire_qs.update(estado=AreaDestinatario.ESTADO_BORRADOR, fecha_asignacion=timezone.now())
			# Registrar para diagnóstico
			try:
				logger.debug("_sync: expired contenido_ids=%s", expired_contenido_ids)
			except Exception:
				pass

		return promoted, expired
	except Exception:
		# No queremos romper la vista por fallos en sincronización
		return 0, 0


def mural_principal(request, area_id=None):
	groups = _group_areas_by_categoria()

	if area_id is not None:
		area_actual = get_object_or_404(Area, pk=area_id)
	else:
		area_cookie = request.COOKIES.get('area_actual_id')
		area_actual = None
		if area_cookie:
			try:
				area_actual = Area.objects.get(pk=int(area_cookie))
			except Exception:
				area_actual = None
		if not area_actual:
			first_group = groups[0] if groups else None
			area_actual = _first_area_from_group(first_group)

	contenidos = _published_contenidos_for_area(area_actual) if area_actual else _published_contenidos_all()

	contexto = {'areas': groups, 'area_actual': area_actual, 'contenidos': contenidos}
	response = render(request, 'mural_principal.html', contexto)
	try:
		if area_actual:
			# set SameSite to Lax to avoid browser warnings; do not force Secure here
			# because local development may be HTTP. In production consider using
			# samesite='None' with secure=True if cross-site usage is required.
			response.set_cookie('area_actual_id', str(area_actual.id), max_age=60 * 60 * 24 * 365, samesite='Lax')
	except Exception:
		pass
	return response


def index(request):
	"""Página de bienvenida con selección por niveles (Index).

	Renderiza cuatro listas filtradas de `Area` por `nivel_formacion`.
	Al hacer click en una carrera redirige a la vista `mural_principal` para esa área.
	"""
	try:
		areas_u = Area.objects.filter(nivel_formacion=Area.NIVEL_U).order_by('nombre')
	except Exception:
		areas_u = Area.objects.none()
	try:
		areas_ip = Area.objects.filter(nivel_formacion=Area.NIVEL_IP).order_by('nombre')
	except Exception:
		areas_ip = Area.objects.none()
	try:
		areas_cft = Area.objects.filter(nivel_formacion=Area.NIVEL_CFT).order_by('nombre')
	except Exception:
		areas_cft = Area.objects.none()
	try:
		areas_gen = Area.objects.filter(nivel_formacion=Area.NIVEL_GEN).order_by('nombre')
	except Exception:
		areas_gen = Area.objects.none()

	return render(request, 'mural/index.html', {
		'areas_u': areas_u,
		'areas_ip': areas_ip,
		'areas_cft': areas_cft,
		'areas_gen': areas_gen,
	})


@login_required
def contenidos_mis_areas(request):
	estado_q = request.GET.get('estado')
	filtro_estado = estado_q if estado_q else None
	area_q = request.GET.get('area')
	selected_area = int(area_q) if area_q and area_q.isdigit() else None

	# Sincronizar estados de publicación (promover programadas y demotar expiradas)
	try:
		promoted_count, expired_count = _sync_publication_states()
		# if settings.DEBUG and (promoted_count or expired_count):
		#	messages.debug(request, f"Sync publication: promoted={promoted_count} expired={expired_count}")
	except Exception:
		# proteger la vista ante cualquier fallo de sincronización
		pass

	user = request.user
	allowed_areas = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct() if not user.is_superuser else Area.objects.all()

	# Perfil: calcular rol asociado a través de AsignacionArea (si existe)
	profile_role = None
	try:
		asig = AsignacionArea.objects.filter(usuario=user).select_related('area').first()
		if asig:
			# Preferir etiqueta legible si está disponible
			get_display = getattr(asig, 'get_rol_display', None)
			if callable(get_display):
				profile_role = get_display()
			else:
				profile_role = str(getattr(asig, 'rol', '') or '')
	except Exception:
		profile_role = None

	# Permiso para gestionar usuarios: superuser o Jefe de área
	can_manage_users = False
	try:
		if request.user.is_superuser:
			can_manage_users = True
		else:
			# si tiene alguna asignación como Jefe de área, puede gestionar usuarios de sus áreas
			can_manage_users = AsignacionArea.objects.filter(usuario=request.user, rol=AsignacionArea.ROL_JEFE).exists()
	except Exception:
		can_manage_users = False

	# Si puede gestionar usuarios, preparar la lista para el template
	users_list = []
	all_areas = []
	if can_manage_users:
		User = get_user_model()
		try:
			if request.user.is_superuser or request.user.is_staff:
				users_qs = User.objects.all()
			else:
				users_qs = User.objects.filter(asignaciones_area__area__in=allowed_areas).distinct()
			# construir lista ligera para la plantilla
			for u in users_qs.order_by('first_name','last_name'):
				# áreas y rol principal
				areas_qs = Area.objects.filter(Q(usuarios=u) | Q(usuario=u)).distinct()
				areas = [a.nombre for a in areas_qs]
				areas_ids = [a.id for a in areas_qs]
				# determinar rol por asignación en las áreas que el current user puede ver
				rol_obj = AsignacionArea.objects.filter(usuario=u, area__in=allowed_areas).first()
				if u.is_superuser:
					display_role = 'Administrador'
				elif rol_obj:
					display_role = getattr(rol_obj, 'rol', '')
				else:
					display_role = ''
				users_list.append({'id': u.id, 'nombre': u.get_full_name() or u.username, 'email': u.email, 'areas': areas, 'areas_ids': areas_ids, 'role': display_role})
		except Exception:
			users_list = []
		# lista de áreas para el select del modal
		try:
			if request.user.is_superuser or request.user.is_staff:
				all_areas = list(Area.objects.all().order_by('nombre'))
			else:
				all_areas = list(allowed_areas.order_by('nombre'))
		except Exception:
			all_areas = []

	# Manejo de actualización de perfil enviado desde la plantilla
	if request.method == 'POST' and request.POST.get('profile_update'):
		try:
			first_name = (request.POST.get('first_name') or '').strip()
			last_name = (request.POST.get('last_name') or '').strip()
			# aceptar distintos nombres de campo según la plantilla/usos previos
			new_pw = (request.POST.get('password1') or request.POST.get('new_password') or request.POST.get('password') or '')
			new_pw_confirm = (request.POST.get('password2') or request.POST.get('new_password_confirm') or request.POST.get('password_confirm') or '')
			# Validar coincidencia de contraseñas si se proporcionan
			if new_pw or new_pw_confirm:
				if new_pw != new_pw_confirm:
					messages.error(request, 'Las contraseñas no coinciden.')
					return redirect('contenidos_mis_areas')
			# Aplicar cambios
			changed = False
			if first_name != user.first_name:
				user.first_name = first_name
				changed = True
			if last_name != user.last_name:
				user.last_name = last_name
				changed = True
			if new_pw:
				# Usar el mecanismo de Django para establecer contraseña
				user.set_password(new_pw)
				changed = True
			if changed:
				user.save()
				# Si se cambió la contraseña, mantener la sesión activa
				if new_pw:
					try:
						update_session_auth_hash(request, user)
					except Exception:
						# no fatal; la sesión puede expirar y el usuario deberá reautenticar
						pass
			messages.success(request, 'Perfil actualizado correctamente.')
			return redirect('contenidos_mis_areas')
		except Exception:
			messages.error(request, 'Error al actualizar el perfil.')
			return redirect('contenidos_mis_areas')

	if user.is_superuser:
		contenidos = Contenido.objects.all()
	else:
		if allowed_areas.exists():
			contenidos = Contenido.objects.filter(Q(area_origen__in=allowed_areas) | Q(destinatarios__area__in=allowed_areas)).distinct()
		else:
			messages.error(request, 'Su usuario no tiene un área asignada.')
			contenidos = Contenido.objects.none()

	# Filtrar por estado (estado es atributo de AreaDestinatario)
	# Nota: cuando el filtro es 'PUBLICADO' queremos mostrar todos los contenidos
	# relacionados a las áreas del usuario independientemente del estado (PUBLICADO/EN_ESPERA/EXPIRADO).
	if filtro_estado and filtro_estado != AreaDestinatario.ESTADO_PUBLICADO:
		contenidos = contenidos.filter(destinatarios__estado=filtro_estado).distinct()

	# Filtrar por área seleccionada
	if selected_area:
		contenidos = contenidos.filter(Q(area_origen__id=selected_area) | Q(destinatarios__area__id=selected_area)).distinct()

	# Formulario para creación/edición
	form = ContenidoForm(user=request.user)

	# Determinar si el usuario es DAE-like: superuser o está relacionado a áreas de nivel GEN
	try:
		is_dae_like = True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()
		if user.is_superuser or is_dae_like:
			# superuser y usuarios DAE-like pueden ver todas las áreas y elegir niveles
			form.fields['destinatarios'].queryset = Area.objects.all()
			can_choose_multiple_origins = True
		else:
			# usuarios normales ven sólo sus áreas
			form.fields['destinatarios'].queryset = allowed_areas
			can_choose_multiple_origins = False
			_default_area = _user_default_area(user, allowed_areas)
			if _default_area:
				form.initial['area_origen'] = _default_area
		# por defecto, preseleccionar en destinatarios las áreas relacionadas al usuario
		try:
			if not user.is_superuser:
				form.initial['destinatarios'] = list(allowed_areas.values_list('id', flat=True))
		except Exception:
			pass
	except Exception:
		# proteger en caso de errores al determinar permisos
		can_choose_multiple_origins = False

	# Asegurar que el widget del select multiple tenga un id y clases consistentes
	try:
		if 'destinatarios' in form.fields:
			form.fields['destinatarios'].widget = django_forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select is-multiple is-fullwidth"})
			# Forzar choices también puede ayudar a algunos widgets a renderizar correctamente
			try:
				qs = form.fields['destinatarios'].queryset
				form.fields['destinatarios'].choices = [(a.id, str(a)) for a in qs]
			except Exception:
				pass
	except Exception:
		# no romper la vista por fallos en la preparación del widget
		pass

	filter_areas = Area.objects.all().order_by('nombre') if user.is_superuser else allowed_areas.order_by('nombre')

	# Preparar lista de contenidos y calcular estado agregado por contenido
	contenidos_list = list(contenidos.order_by('-fecha_creacion'))
	for c in contenidos_list:
		try:
			# Obtener todos los estados por defecto
			dest_states = list(c.destinatarios.values_list('estado', flat=True))
			# Si se indicó un área seleccionada, priorizar el estado para esa área si existe
			if selected_area:
				area_states = list(c.destinatarios.filter(area_id=selected_area).values_list('estado', flat=True))
				if area_states:
					dest_states = area_states

			# Determinar estado agregado con prioridad PUBLICADO > EN_ESPERA > EXPIRADO
			if AreaDestinatario.ESTADO_PUBLICADO in dest_states:
				c_state = AreaDestinatario.ESTADO_PUBLICADO
			elif AreaDestinatario.ESTADO_EN_ESPERA in dest_states:
				c_state = AreaDestinatario.ESTADO_EN_ESPERA
			elif AreaDestinatario.ESTADO_EXPIRADO in dest_states:
				c_state = AreaDestinatario.ESTADO_EXPIRADO
			elif dest_states:
				c_state = dest_states[0]
			else:
				c_state = AreaDestinatario.ESTADO_BORRADOR

			# Decidir cómo presentar EN_ESPERA:
			# - Si existen asociaciones EN_ESPERA con fecha_asignacion en el futuro,
			#   el contenido debe mostrarse como 'EN_ESPERA' (programado).
			# - En otros casos (EN_ESPERA sin fecha futura o EXPIRADO) mostrar 'BORRADOR'.
			try:
				now_check = timezone.now()
				if c_state == AreaDestinatario.ESTADO_EN_ESPERA:
					# comprobar si alguna asociación tiene fecha_asignacion futura
					future_exists = c.destinatarios.filter(estado=AreaDestinatario.ESTADO_EN_ESPERA, fecha_asignacion__gt=now_check).exists()
					if future_exists:
						c.computed_estado = AreaDestinatario.ESTADO_EN_ESPERA
					else:
						c.computed_estado = AreaDestinatario.ESTADO_BORRADOR
				elif c_state == AreaDestinatario.ESTADO_EXPIRADO:
					c.computed_estado = AreaDestinatario.ESTADO_BORRADOR
				else:
					c.computed_estado = c_state

				# Calcular una fecha límite representativa para mostrar en listados.
				try:
					min_fecha = c.destinatarios.aggregate(min_fecha=Min('fecha_limite'))['min_fecha']
					c.display_fecha_limite = min_fecha
				except Exception:
					c.display_fecha_limite = None
			except Exception:
				c.computed_estado = c_state

			# Flags auxiliares para la plantilla: si existe PUBLICADO para el area seleccionada y en general
			try:
				if selected_area:
					c.has_published_for_selected_area = c.destinatarios.filter(area_id=selected_area, estado=AreaDestinatario.ESTADO_PUBLICADO).exists()
				else:
					c.has_published_for_selected_area = False
				c.has_any_published = c.destinatarios.filter(estado=AreaDestinatario.ESTADO_PUBLICADO).exists()
			except Exception:
				c.has_published_for_selected_area = False
				c.has_any_published = False

			# Permiso de edición por contenido:
			# - superuser puede editar todo
			# - si el contenido fue originado por un área GEN, solo usuarios DAE-like (o superuser) pueden editar
			# - en otros casos, pueden editar usuarios relacionados a area_origen o destinatarios
			try:
				if user.is_superuser:
					c.can_edit = True
				elif c.area_origen and c.area_origen.nivel_formacion == Area.NIVEL_GEN:
					c.can_edit = is_dae_like
				else:
					c.can_edit = ((c.area_origen in allowed_areas) or c.destinatarios.filter(area__in=allowed_areas).exists())
			except Exception:
				c.can_edit = False
		except Exception:
			c.computed_estado = AreaDestinatario.ESTADO_BORRADOR

	return render(request, 'operatividad/gest_contenidos.html', {
		'contenidos': contenidos_list,
		'form': form,
		'accion': 'Crear',
		'can_choose_multiple_origins': can_choose_multiple_origins,
		'can_choose_levels': can_choose_multiple_origins,
		'filter_estado': filtro_estado,
		'filter_areas': filter_areas,
		'selected_area': selected_area,
		'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
		'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
		'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
		'profile_role': profile_role,
		'can_manage_users': can_manage_users,
		'users_list': users_list,
		'all_areas': all_areas,
	})



@login_required
def contenido_crear(request):
	user = request.user
	allowed_areas = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct() if not user.is_superuser else Area.objects.all()
	if not user.is_superuser and not allowed_areas.exists():
		messages.error(request, 'Su usuario no tiene un área asignada (rol/área).')
		return redirect('contenidos_mis_areas')

	# bandera de multi-origen (DAE-like): superuser o usuario relacionado a áreas GEN
	can_multi = True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()

	# Inicializar `area_origen` con la heurística por defecto para evitar
	# UnboundLocalError cuando la vista se renderiza en GET (antes de cualquier POST).
	area_origen = None
	try:
		area_origen = _user_default_area(user, allowed_areas)
	except Exception:
		area_origen = None
	if not area_origen:
		try:
			area_origen = allowed_areas.first() if allowed_areas.exists() else (Area.objects.first() if Area.objects.exists() else None)
		except Exception:
			area_origen = None

	form = ContenidoForm(request.POST or None, user=request.user)
	try:
		if user.is_superuser:
			form.fields['area_origen'].queryset = Area.objects.all()
			form.fields['area_origen_multiple'].queryset = Area.objects.all()
			form.fields['destinatarios'].queryset = Area.objects.all()
		else:
			form.fields['area_origen'].queryset = allowed_areas
			form.fields['area_origen_multiple'].queryset = allowed_areas
			# destinatarios disponibles por defecto se limitan a las áreas del usuario
			# si el usuario es DAE-like (pertenece a GEN) permitir ver todas las áreas
			is_dae_like = Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()
			if is_dae_like:
				form.fields['destinatarios'].queryset = Area.objects.all()
			else:
				form.fields['destinatarios'].queryset = allowed_areas
			# Si el usuario puede elegir múltiples orígenes (DAE/superuser), no habilitamos un select adicional
	except Exception:
		pass

	# Asegurar widget consistente para el select multiple en la vista de creación
	try:
		if 'destinatarios' in form.fields:
			form.fields['destinatarios'].widget = django_forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select is-multiple is-fullwidth"})
			try:
				qs2 = form.fields['destinatarios'].queryset
				form.fields['destinatarios'].choices = [(a.id, str(a)) for a in qs2]
			except Exception:
				pass
	except Exception:
		pass
	# Preseleccionar automáticamente las áreas del usuario en creación (si no es POST)
	try:
		if request.method != 'POST' and 'destinatarios' in form.fields:
			try:
				form.initial['destinatarios'] = list(form.fields['destinatarios'].queryset.values_list('id', flat=True))
			except Exception:
				pass
	except Exception:
		pass

	if request.method == 'POST' and form.is_valid():
		# En DEBUG mostrar el contenido bruto del POST para depuración de la plantilla
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				raw_post = {k: request.POST.getlist(k) for k in ['destinatarios','niveles_destino']}
				# messages.info(request, f"DEBUG POST raw: {raw_post}")
				try:
					logger.debug("DEBUG POST raw: %s", raw_post)
				except Exception:
					pass
		except Exception:
			pass
		# Acción y fecha programada
		# Puede que el formulario envíe múltiples valores con el mismo nombre
		# (p. ej. un hidden + el botón). Tomar la última ocurrencia evita
		# ambigüedades entre 'borrador' y 'publicar'.
		accion_list = request.POST.getlist('accion')
		# Usar la última ocurrencia enviada por el formulario (el botón clickeado
		# normalmente aparece al final). No priorizar 'publicar' para respetar
		# explícitamente la elección del usuario (p. ej. 'borrador').
		accion = accion_list[-1] if accion_list else request.POST.get('accion')
		scheduled = form.cleaned_data.get('fecha_publicacion_programada') if hasattr(form, 'cleaned_data') else None
		fecha_limite = form.cleaned_data.get('fecha_limite') if hasattr(form, 'cleaned_data') else None
		# Normalizar scheduled a timezone-aware si viene naive (browser datetime-local suele ser naive)
		try:
			if scheduled and timezone.is_naive(scheduled):
				scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())
		except Exception:
			# si falla la normalización, dejar el valor original (se tratará como immediate)
			pass
		# Normalizar fecha_limite si viene naive
		try:
			if fecha_limite and timezone.is_naive(fecha_limite):
				fecha_limite = timezone.make_aware(fecha_limite, timezone.get_current_timezone())
		except Exception:
			pass

		# Determinar si se debe publicar inmediatamente
		now = timezone.now()
		if scheduled:
			# si la fecha programada ya pasó o es igual, publicar ahora
			will_publish_now = scheduled <= now
		else:
			will_publish_now = (accion == 'publicar')

		# DEBUG: registrar la decisión de publicación para rastrear problemas
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				pass  # debug message commented out
		except Exception:
			pass

		# Determinar área origen: viene del POST (campo oculto) o tomar la primera área permitida
		# Determinar área origen: preferir valor enviado por POST (campo oculto `area_origen`),
		# luego usar heurística por defecto del usuario.
		area_origen = None
		# Si el formulario fue enviado, respetar el área indicada (siempre que el usuario tenga permiso)
		if request.method == 'POST':
			post_area = request.POST.get('area_origen')
			if post_area:
				try:
					_candidate = Area.objects.get(pk=int(post_area))
					# permitir sólo si es superuser o la área está dentro de allowed_areas
					if user.is_superuser or allowed_areas.filter(pk=_candidate.pk).exists():
						area_origen = _candidate
				except Exception:
					area_origen = None
		# si no vino por POST, calcular valor por defecto usando la heurística existente
		if not area_origen:
			try:
				area_origen = _user_default_area(user, allowed_areas)
			except Exception:
				area_origen = None
		# fallback: si no se resolvió, usar la primera área permitida (evitar NOT NULL)
		if not area_origen:
			try:
				area_origen = allowed_areas.first() if allowed_areas.exists() else (Area.objects.first() if Area.objects.exists() else None)
			except Exception:
				area_origen = None

		# Crear único Contenido (siempre una sola instancia); destinatarios múltiples se fusionan más abajo
		contenido = form.save(commit=False)
		# Si se seleccionó 'OTRO' para tipo_contenido, usar el valor enviado en el input adicional
		try:
			if form.cleaned_data.get('tipo_contenido') == Contenido.TIPO_OTRO:
				custom = request.POST.get('tipo_contenido_otro', '').strip()
				max_len = Contenido._meta.get_field('tipo_contenido').max_length
				if not custom:
					form.add_error('tipo_contenido', 'Debe especificar el tipo cuando selecciona "Otro".')
					# Re-renderizar formulario con errores
					return render(request, 'operatividad/gest_contenidos.html', {
						'form': form,
						'accion': 'Crear',
						'contenidos': Contenido.objects.filter(area_origen__in=allowed_areas).order_by('-fecha_creacion'),
						'default_area_id': area_origen.id if area_origen else None,
						'can_choose_multiple_origins': can_multi,
						'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
						'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
						'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
					})
				if len(custom) > max_len:
					form.add_error('tipo_contenido', f'El tipo especificado es demasiado largo (máx. {max_len} caracteres).')
					return render(request, 'operatividad/gest_contenidos.html', {
						'form': form,
						'accion': 'Crear',
						'contenidos': Contenido.objects.filter(area_origen__in=allowed_areas).order_by('-fecha_creacion'),
						'default_area_id': area_origen.id if area_origen else None,
						'can_choose_multiple_origins': can_multi,
						'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
						'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
						'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
					})
				contenido.tipo_contenido = custom
		except Exception:
			pass
		# Not storing global fecha_publicado on Contenido; publication is tracked per AreaDestinatario
		# asignar area_origen si existe
		if area_origen:
			contenido.area_origen = area_origen

		contenido.save()
		# attach files
		for f in request.FILES.getlist('archivo_adjunto'):
			a = ArchivoModel(contenido=contenido, archivo=f)
			try:
				a.full_clean()
				a.save()
			except ValidationError:
				pass

		# Continuar con flujo normal usando la instancia guardada `contenido`
		# Destinatarios seleccionados (multi-select)
		# Destinatarios pueden ser específicos o por nivel (niveles_destino)
		try:
			selected_levels = form.cleaned_data.get('niveles_destino') or []
			if selected_levels:
				# expandir niveles y usar esos destinos
				destinos = list(Area.objects.filter(nivel_formacion__in=selected_levels))
			else:
				destinos = list(form.cleaned_data.get('destinatarios') or [])
		except Exception:
			destinos = []

		# Filtrar destinos por permisos también en edición
		try:
			is_dae_like = True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()
			if not is_dae_like and not user.is_superuser:
				allowed_set = set(allowed_areas.values_list('id', flat=True))
				filtered = [a for a in destinos if getattr(a, 'id', None) in allowed_set]
				if len(filtered) != len(destinos):
					removed = [str(a) for a in destinos if getattr(a, 'id', None) not in allowed_set]
					messages.warning(request, f"Algunas áreas seleccionadas quedaron fuera de su alcance y fueron excluidas: {removed}")
				destinos = filtered
		except Exception:
			pass

		# Filtrar destinos por permisos: si el usuario NO es DAE-like ni superuser, solo permitir allowed_areas
		try:
			is_dae_like = True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()
			if not is_dae_like and not user.is_superuser:
				allowed_set = set(allowed_areas.values_list('id', flat=True))
				filtered = [a for a in destinos if getattr(a, 'id', None) in allowed_set]
				if len(filtered) != len(destinos):
					# informar que algunos destinos fueron removidos por permisos
					removed = [str(a) for a in destinos if getattr(a, 'id', None) not in allowed_set]
					messages.warning(request, f"Algunas áreas seleccionadas quedaron fuera de su alcance y fueron excluidas: {removed}")
				destinos = filtered
		except Exception:
			pass

		# Mostrar cleaned_data en edición para depuración (DEBUG)
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				# cd = (form.cleaned_data.get('destinatarios'), form.cleaned_data.get('niveles_destino'))
				pass  # debug message commented out
		except Exception:
			pass

		# Depuración: mostrar qué destinos se resolvieron (solo en DEBUG)
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				names = [str(a) for a in destinos]
				# messages.info(request, f"DEBUG destinos resueltos: {names}")
				# también mostrar lo que quedó en cleaned_data
				try:
					cd = (form.cleaned_data.get('destinatarios'), form.cleaned_data.get('niveles_destino'))
					# messages.info(request, f"DEBUG cleaned fields: {cd}")
				except Exception:
					pass
		except Exception:
			pass

		# Si el usuario intentó publicar pero no seleccionó destinatarios, informar
		if accion == 'publicar' and (not destinos or len(destinos) == 0):
			messages.error(request, 'Para publicar debe seleccionar al menos una carrera o nivel destinatario.')
			# volver a mostrar el formulario con mensajes
			return render(request, 'operatividad/gest_contenidos.html', {
				'form': form,
				'accion': 'Crear',
				'contenidos': Contenido.objects.filter(area_origen__in=allowed_areas).order_by('-fecha_creacion'),
				'default_area_id': area_origen.id if area_origen else None,
				'can_choose_multiple_origins': can_multi,
				'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
				'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
				'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
			})

		# continuar con la creación de AreaDestinatario...

		# Crear/actualizar AreaDestinatario para cada destino seleccionado
		created_for_publish = []
		for area_dest in destinos:
			# asegurar que area_dest es instancia de Area (puede venir como id en casos raros)
			if not hasattr(area_dest, 'id'):
				try:
					area_dest = Area.objects.get(pk=int(area_dest))
				except Exception:
					continue
			try:
				# decidir estado objetivo: PRIORIDAD al botón seleccionado (accion)
				# 1) Si el usuario solicitó 'borrador' => forzar BORRADOR (ignorar fechas)
				# 2) Si solicitó 'publicar' => validar expiración y programación
				# 3) Si se programó para el futuro => EN_ESPERA con fecha programada
				if accion == 'borrador':
					estado_target = AreaDestinatario.ESTADO_BORRADOR
					fecha_asig = timezone.now()
				else:
					# programado en el futuro tiene prioridad sobre publicación inmediata
					if scheduled and scheduled > now:
						estado_target = AreaDestinatario.ESTADO_EN_ESPERA
						fecha_asig = scheduled
					else:
						if accion == 'publicar':
							# si la publicación ya está expirada según la fecha indicada en el formulario, no publicar: dejar Borrador
							if fecha_limite and fecha_limite < now:
								estado_target = AreaDestinatario.ESTADO_BORRADOR
								fecha_asig = timezone.now()
							else:
								estado_target = AreaDestinatario.ESTADO_PUBLICADO
								fecha_asig = timezone.now()
						else:
							# por defecto, tratar como borrador explícito
							estado_target = AreaDestinatario.ESTADO_BORRADOR
							fecha_asig = timezone.now()

				ad, created = AreaDestinatario.objects.get_or_create(
					area=area_dest,
					contenido=contenido,
					defaults={'estado': estado_target, 'fecha_limite': fecha_limite, 'fecha_asignacion': fecha_asig}
				)
				# Asegurar la persistencia de las intenciones: debido a que
				# `fecha_asignacion` en el modelo usa `auto_now_add`, la fecha
				# pasada en `defaults` puede haberse ignorado y se habrá escrito
				# la hora actual. Forzar actualización aquí para reflejar la
				# intención (p. ej. poner una fecha lejana para borrador).
				need_save = False
				if ad.estado != estado_target:
					ad.estado = estado_target
					need_save = True
				# actualizar fecha_asignacion siempre que difiera de la intención
				if fecha_asig and (ad.fecha_asignacion is None or ad.fecha_asignacion != fecha_asig):
					ad.fecha_asignacion = fecha_asig
					need_save = True
				if fecha_limite and ad.fecha_limite != fecha_limite:
					ad.fecha_limite = fecha_limite
					need_save = True
				if need_save:
					ad.save()
				# track if this area ended up published
				try:
					if ad.estado == AreaDestinatario.ESTADO_PUBLICADO:
						created_for_publish.append(area_dest.nombre)
				except Exception:
					pass
			except Exception:
				# no interrumpir flujo por errores en destinatarios
				pass

		# DEBUG: listar AreaDestinatario creados/actualizados para este contenido
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				ads = list(AreaDestinatario.objects.filter(contenido=contenido).values('area__nombre','estado','fecha_asignacion'))
				# messages.info(request, f"DEBUG AreaDestinatario after create: {ads}")
				# messages.info(request, f"DEBUG published areas (names): {created_for_publish}")
		except Exception:
			pass

		# Si el usuario intentó publicar, comprobar que al menos un destinatario quedó PUBLICADO
		if accion == 'publicar':
			pub_count = AreaDestinatario.objects.filter(contenido=contenido, estado=AreaDestinatario.ESTADO_PUBLICADO).count()
			if pub_count == 0:
				# Si la publicación fue programada para el futuro, aceptar como éxito programado
				if scheduled and scheduled > now:
					messages.success(request, f'Contenido programado para publicación el {scheduled.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M")}.')
					return redirect('contenidos_mis_areas')
				# Debug info to help diagnose why none were created
				try:
					dest_names = [str(d) for d in destinos]
				except Exception:
					dest_names = []
				existing_ads = list(AreaDestinatario.objects.filter(contenido=contenido).values('area__nombre','estado'))
				messages.error(request, 'No se pudo publicar: no se crearon destinatarios con estado PUBLICADO. Seleccione destinatarios o niveles.')
				# attach debug messages only in DEBUG
				from django.conf import settings as _dj_settings
				if getattr(_dj_settings, 'DEBUG', False):
					pass  # debug messages commented out
				# Volver a mostrar el formulario para corregir
				return render(request, 'operatividad/gest_contenidos.html', {
					'form': form,
					'accion': 'Crear',
					'contenidos': Contenido.objects.filter(area_origen__in=allowed_areas).order_by('-fecha_creacion'),
					'default_area_id': area_origen.id if area_origen else None,
					'can_choose_multiple_origins': can_multi,
					'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
					'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
					'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
				})
		messages.success(request, 'Contenido creado.')
		return redirect('contenidos_mis_areas')

	contenidos = Contenido.objects.filter(area_origen__in=allowed_areas).order_by('-fecha_creacion')
	# Ensure destinatarios choices are populated so template widget renders options
	try:
		qs_check = form.fields['destinatarios'].queryset
		form.fields['destinatarios'].choices = [(a.id, str(a)) for a in qs_check]
	except Exception:
		pass
	return render(request, 'operatividad/gest_contenidos.html', {
		'form': form,
		'accion': 'Crear',
		'contenidos': contenidos,
		'default_area_id': area_origen.id if area_origen else None,
		'can_choose_multiple_origins': can_multi,
		'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
		'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
		'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
		})


@login_required
def contenido_editar(request, pk):
	contenido = get_object_or_404(Contenido, pk=pk)
	user = request.user
	allowed_areas = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct() if not user.is_superuser else Area.objects.all()

	# Permitir que cualquier usuario abra el formulario de edición.
	# Las restricciones de permisos se aplican al guardar (no eliminar
	# destinatarios que el usuario no puede manejar, y evitar que agregue
	# nuevos destinatarios fuera de su alcance).

	form = ContenidoForm(request.POST or None, instance=contenido, user=request.user)
	try:
		if not user.is_superuser:
			# permitir que el select de destinatarios incluya tanto las áreas
			# a las que el usuario pertenece como las áreas ya relacionadas al contenido,
			# de modo que en edición no desaparezcan las opciones existentes.
			content_area_ids = list(contenido.destinatarios.values_list('area_id', flat=True))
			union_qs = Area.objects.filter(Q(id__in=content_area_ids) | Q(id__in=allowed_areas.values_list('id', flat=True))).distinct()
			# Asegurar queryset y widget para que el select multiple muestre opciones y selecciones
			form.fields['destinatarios'].queryset = union_qs
			form.fields['destinatarios'].widget = django_forms.SelectMultiple(attrs={"id": "form-destinatarios", "class": "select is-multiple is-fullwidth"})
			form.fields['area_origen'].queryset = allowed_areas
			# Forzar choices (por si el widget no renderiza correctamente la queryset)
			try:
				form.fields['destinatarios'].choices = [(a.id, str(a)) for a in union_qs]
			except Exception:
				pass
			# Debug: mostrar cuántas opciones y cuáles estaban preseleccionadas
			try:
				if settings.DEBUG:
					msgs = f"Edit form destinatarios: qs_count={form.fields['destinatarios'].queryset.count()} initial={list(content_area_ids)}"
					# messages.info(request, msgs)
			except Exception:
				pass
	except Exception:
		pass

	# Preseleccionar destinatarios existentes para el formulario
	try:
		ids = list(contenido.destinatarios.values_list('area_id', flat=True))
		form.initial['destinatarios'] = ids
		# también asegurar que el field tenga los valores iniciales (algunos widgets lo requieren)
		try:
			form.fields['destinatarios'].initial = ids
		except Exception:
			pass
	except Exception:
		pass

	if request.method == 'POST' and form.is_valid():
		contenido_editado = form.save(commit=False)
		# Si el formulario incluye un campo oculto `area_origen`, respetarlo
		# sólo si el usuario tiene permiso para asignar esa área.
		post_area = request.POST.get('area_origen')
		if post_area:
			try:
				_candidate = Area.objects.get(pk=int(post_area))
				if user.is_superuser or allowed_areas.filter(pk=_candidate.pk).exists():
					contenido_editado.area_origen = _candidate
			except Exception:
				# ignorar si no es válido
				pass
		# acción enviada desde la plantilla: 'publicar' | 'borrador'
		accion_list = request.POST.getlist('accion')
		# Usar la última ocurrencia enviada por el formulario para respetar
		# el botón realmente clickeado por el usuario.
		accion = accion_list[-1] if accion_list else request.POST.get('accion')
		# fecha programada (opcional)
		scheduled = form.cleaned_data.get('fecha_publicacion_programada') if hasattr(form, 'cleaned_data') else None
		fecha_limite = form.cleaned_data.get('fecha_limite') if hasattr(form, 'cleaned_data') else None
		try:
			if scheduled and timezone.is_naive(scheduled):
				scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())
		except Exception:
			pass
		# normalizar fecha_limite si viene naive
		try:
			if fecha_limite and timezone.is_naive(fecha_limite):
				fecha_limite = timezone.make_aware(fecha_limite, timezone.get_current_timezone())
		except Exception:
			pass
		now = timezone.now()
		if scheduled:
			will_publish_now = scheduled <= now
		else:
			will_publish_now = (accion == 'publicar')

		# DEBUG: registrar la decisión de publicación para diagnóstico
		try:
			from django.conf import settings as _dj_settings
			if getattr(_dj_settings, 'DEBUG', False):
				pass  # debug message commented out
		except Exception:
			pass

		# Not storing global fecha_publicado on Contenido; publication is tracked per AreaDestinatario
		# Si se seleccionó 'OTRO' para tipo_contenido, usar el valor enviado en el input adicional
		try:
			if form.cleaned_data.get('tipo_contenido') == Contenido.TIPO_OTRO:
				custom = request.POST.get('tipo_contenido_otro', '').strip()
				max_len = Contenido._meta.get_field('tipo_contenido').max_length
				if not custom:
					form.add_error('tipo_contenido', 'Debe especificar el tipo cuando selecciona "Otro".')
					return render(request, 'operatividad/gest_contenidos.html', {
						'form': form,
						'accion': 'Editar',
						'contenido': contenido,
						'contenidos': Contenido.objects.filter(area_origen=contenido.area_origen).order_by('-fecha_creacion'),
						'default_area_id': contenido.area_origen.id if getattr(contenido, 'area_origen', None) else None,
						'can_choose_multiple_origins': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
						'can_choose_levels': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
						'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
						'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
						'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
						'debug_dest_qs': list(form.fields['destinatarios'].queryset.values('id','nombre')) if getattr(settings, 'DEBUG', False) else None,
						'debug_initial_ids': form.initial.get('destinatarios') if getattr(settings, 'DEBUG', False) else None,
					})
				if len(custom) > max_len:
					form.add_error('tipo_contenido', f'El tipo especificado es demasiado largo (máx. {max_len} caracteres).')
					return render(request, 'operatividad/gest_contenidos.html', {
						'form': form,
						'accion': 'Editar',
						'contenido': contenido,
						'contenidos': Contenido.objects.filter(area_origen=contenido.area_origen).order_by('-fecha_creacion'),
						'default_area_id': contenido.area_origen.id if getattr(contenido, 'area_origen', None) else None,
						'can_choose_multiple_origins': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
						'can_choose_levels': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
						'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
						'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
						'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
						'debug_dest_qs': list(form.fields['destinatarios'].queryset.values('id','nombre')) if getattr(settings, 'DEBUG', False) else None,
						'debug_initial_ids': form.initial.get('destinatarios') if getattr(settings, 'DEBUG', False) else None,
					})
				contenido_editado.tipo_contenido = custom
		except Exception:
			pass
		contenido_editado.save()

		# Procesar eliminación de archivos existentes solicitada desde la plantilla
		# Se espera que la plantilla envíe múltiples valores 'remove_archivos' con los ids a eliminar
		try:
			remove_ids = request.POST.getlist('remove_archivos')
			if remove_ids:
				ids = [int(x) for x in remove_ids if x]
				if ids:
					# eliminar sólo archivos asociados a este contenido por seguridad
					ArchivoModel.objects.filter(id__in=ids, contenido=contenido_editado).delete()
		except Exception:
			# no interrumpir el flujo si ocurre un error al eliminar archivos
			pass
		# sincronizar destinatarios: niveles_destino tienen prioridad
		try:
			selected_levels = form.cleaned_data.get('niveles_destino') or []
			if selected_levels:
				destinos = list(Area.objects.filter(nivel_formacion__in=selected_levels))
			else:
				destinos = list(form.cleaned_data.get('destinatarios') or [])
		except Exception:
			destinos = []

		# En edición, preservar los destinatarios existentes que el usuario no
		# tiene permiso para modificar (evitar eliminarlos accidentalmente).
		try:
			is_dae_like = True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists()
			if not is_dae_like and not user.is_superuser:
				allowed_set = set(allowed_areas.values_list('id', flat=True))
				# Destinos que el usuario puede asignar (seleccionados y dentro de allowed)
				filtered = [a for a in destinos if getattr(a, 'id', None) in allowed_set]
				# Destinos que ya existen en el contenido pero que el usuario NO puede cambiar
				existing_ids = set(contenido.destinatarios.values_list('area_id', flat=True))
				preserved_ids = existing_ids - allowed_set
				preserved_qs = list(Area.objects.filter(id__in=preserved_ids)) if preserved_ids else []
				if len(filtered) != len(destinos):
					removed = [str(a) for a in destinos if getattr(a, 'id', None) not in allowed_set]
					messages.warning(request, f"Algunas áreas seleccionadas quedaron fuera de su alcance y fueron excluidas: {removed}")
				# unir los preservados (sin duplicados)
				preserved_map = {a.id: a for a in preserved_qs}
				final_destinos = {getattr(a, 'id', None): a for a in filtered}
				final_destinos.update(preserved_map)
				destinos = list(final_destinos.values())
		except Exception:
			pass

		# Crear/actualizar AreaDestinatario para cada destino seleccionado
		new_ids = set()
		for area_dest in destinos:
			new_ids.add(area_dest.id)
			try:
				# decidir estado objetivo: PRIORIDAD al botón seleccionado (accion)
				if accion == 'borrador':
					estado_target = AreaDestinatario.ESTADO_BORRADOR
					fecha_asig = timezone.now()
				else:
					if scheduled and scheduled > now:
						estado_target = AreaDestinatario.ESTADO_EN_ESPERA
						fecha_asig = scheduled
					else:
						if accion == 'publicar':
							# si la publicación ya está expirada según la fecha indicada en el formulario, no publicar: dejar Borrador
							if fecha_limite and fecha_limite < now:
								estado_target = AreaDestinatario.ESTADO_BORRADOR
								fecha_asig = timezone.now()
							else:
								estado_target = AreaDestinatario.ESTADO_PUBLICADO
								fecha_asig = timezone.now()
						else:
							estado_target = AreaDestinatario.ESTADO_BORRADOR
							fecha_asig = timezone.now()

				ad, created = AreaDestinatario.objects.get_or_create(
					area=area_dest,
					contenido=contenido_editado,
					defaults={'estado': estado_target, 'fecha_limite': fecha_limite, 'fecha_asignacion': fecha_asig}
				)
				# Forzar persistencia de la intención (ver nota arriba sobre auto_now_add)
				need_save = False
				if ad.estado != estado_target:
					ad.estado = estado_target
					need_save = True
				if fecha_asig and (ad.fecha_asignacion is None or ad.fecha_asignacion != fecha_asig):
					ad.fecha_asignacion = fecha_asig
					need_save = True
				if fecha_limite and ad.fecha_limite != fecha_limite:
					ad.fecha_limite = fecha_limite
					need_save = True
				if need_save:
					ad.save()
			except Exception:
				pass

		# Eliminar destinatarios que ya no estén seleccionados, pero respetando
		# los destinatarios preservados (aquellos fuera del alcance del editor).
		try:
			existing = set(contenido_editado.destinatarios.values_list('area_id', flat=True))
			# recalcular preserved_ids según allowed_areas (si existe)
			if not user.is_superuser:
				allowed_set = set(allowed_areas.values_list('id', flat=True))
				preserved_ids = existing - allowed_set
			else:
				preserved_ids = set()
			to_remove = existing - new_ids - preserved_ids
			if to_remove:
				AreaDestinatario.objects.filter(contenido=contenido_editado, area_id__in=to_remove).delete()
		except Exception:
			pass

		# Si se programó publicación en el futuro, forzar que TODAS las asociaciones
		# queden en EN_ESPERA con la fecha programada y limpiar fecha_publicado
		# del contenido para evitar que se considere publicado.
		try:
			if scheduled and scheduled > now:
				AreaDestinatario.objects.filter(contenido=contenido_editado).update(estado=AreaDestinatario.ESTADO_EN_ESPERA, fecha_asignacion=scheduled)
		except Exception:
			pass

		# Si el usuario solicitó 'borrador', forzar que los destinatarios
		# gestionables pasen a estado EN_ESPERA para despublicar el contenido.
		try:
			if accion == 'borrador':
				# Registrar estados actuales antes de la operación para diagnóstico
				try:
					before = list(AreaDestinatario.objects.filter(contenido=contenido_editado).values('id','area__nombre','estado','fecha_asignacion'))
					# messages.info(request, f"DEBUG pre-unpublish accion={accion} rows={len(before)} estados={before}")
				except Exception:
					pass

				# Forzar despublicación global: actualizar todas las asociaciones del contenido
				try:
					# Usar ESTADO_BORRADOR para reflejar la intención explícita del usuario
					updated = AreaDestinatario.objects.filter(contenido=contenido_editado).update(estado=AreaDestinatario.ESTADO_BORRADOR, fecha_asignacion=timezone.now())
				except Exception:
					updated = None

				# Asegurar que el contenido global deje de considerarse publicado
				try:
					# Publication is tracked at AreaDestinatario level; nothing to clear on Contenido
					pass
				except Exception:
					pass

				# Registrar estados posteriores para diagnóstico
				try:
					after = list(AreaDestinatario.objects.filter(contenido=contenido_editado).values('id','area__nombre','estado','fecha_asignacion'))
					# messages.info(request, f"DEBUG post-unpublish updated={updated} rows={len(after)} estados={after}")
				except Exception:
					pass
		except Exception:
			# no interrumpir flujo por errores en actualización de estados
			pass
		# archivos
		for f in request.FILES.getlist('archivo_adjunto'):
			a = ArchivoModel(contenido=contenido_editado, archivo=f)
			try:
				a.full_clean()
				a.save()
			except ValidationError:
				pass
		messages.success(request, 'Contenido actualizado.')
		return redirect('contenidos_mis_areas')

	contenidos = Contenido.objects.filter(area_origen=contenido.area_origen).order_by('-fecha_creacion')
	# Ensure destinatarios choices are populated so template widget renders options
	try:
		qs_check = form.fields['destinatarios'].queryset
		form.fields['destinatarios'].choices = [(a.id, str(a)) for a in qs_check]
	except Exception:
		pass
	return render(request, 'operatividad/gest_contenidos.html', {
		'form': form,
		'accion': 'Editar',
		'contenido': contenido,
		'contenidos': contenidos,
		# DAE-like detection consistente
		'can_choose_multiple_origins': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
		# permitir mostrar las checkboxes de niveles también en edición cuando proceda
		'can_choose_levels': True if user.is_superuser else Area.objects.filter(Q(usuarios=user) | Q(usuario=user), nivel_formacion=Area.NIVEL_GEN).exists(),
		'allowed_extensions': getattr(settings, 'FILE_UPLOAD_ALLOWED_EXTENSIONS', []),
		'max_size_mb': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_MB', 20),
		'size_by_type': getattr(settings, 'FILE_UPLOAD_MAX_SIZE_BY_TYPE', {}),
		# Debug info for template when DEBUG=True
		'debug_dest_qs': list(form.fields['destinatarios'].queryset.values('id','nombre')) if getattr(settings, 'DEBUG', False) else None,
		'debug_initial_ids': form.initial.get('destinatarios') if getattr(settings, 'DEBUG', False) else None,
		'default_area_id': contenido.area_origen.id if getattr(contenido, 'area_origen', None) else None,
	})



@login_required
def contenido_eliminar(request, pk):
	contenido = get_object_or_404(Contenido, pk=pk)
	user = request.user
	allowed_areas = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct() if not user.is_superuser else Area.objects.all()

	# La interfaz principal usa un modal y envía un POST directamente al endpoint.
	# Comportamiento de eliminación:
	# - Superuser o responsables del área origen pueden eliminar el contenido completo.
	# - Si el contenido fue originado por un área GEN, usuarios relacionados a áreas
	#   específicas pueden eliminar solamente la asociación de su(s) área(s) (AreaDestinatario),
	#   no el contenido global.
	# - En otros casos, si el usuario no está relacionado, no puede eliminar.

	if request.method == 'POST':
		# Caso 1: superuser o responsable del area origen -> eliminación completa
		try:
			origin_is_responsible = (not user.is_superuser) and (contenido.area_origen in allowed_areas)
		except Exception:
			origin_is_responsible = False

		if user.is_superuser or origin_is_responsible:
			contenido.delete()
			messages.success(request, 'Contenido eliminado correctamente.')
			return redirect('contenidos_mis_areas')

		# Caso 2: contenido originado por área GEN -> permitir que usuarios de áreas
		# específicas eliminen solo su asociación (unpublish para su area)
		try:
			if contenido.area_origen and contenido.area_origen.nivel_formacion == Area.NIVEL_GEN:
				# cuáles de las allowed_areas están asociadas como destinatarios a este contenido
				user_area_ids = set(allowed_areas.values_list('id', flat=True)) if not user.is_superuser else set()
				content_dest_ids = set(contenido.destinatarios.values_list('area_id', flat=True))
				intersect = user_area_ids & content_dest_ids
				if intersect:
					# eliminar sólo las asociaciones para las áreas del usuario
					AreaDestinatario.objects.filter(contenido=contenido, area_id__in=list(intersect)).delete()
					messages.success(request, 'Contenido removido para su(s) área(s).')
					return redirect('contenidos_mis_areas')
				else:
					messages.error(request, 'No tiene permiso para eliminar este contenido.')
					return redirect('contenidos_mis_areas')
		except Exception:
			messages.error(request, 'Error al procesar la eliminación.')
			return redirect('contenidos_mis_areas')

		# Caso 3: no tiene permiso para eliminar
		messages.error(request, 'No tiene permiso para eliminar este contenido.')
		return redirect('contenidos_mis_areas')

	# Redirigir en GET al listado principal (el modal maneja la confirmación)
	return redirect('contenidos_mis_areas')


@login_required
def ir_a_mis_areas(request):
	user = request.user
	if user.is_superuser:
		return redirect(reverse('mural_principal'))

	areas = Area.objects.filter(Q(usuarios=user) | Q(usuario=user)).distinct()
	if areas.count() == 1:
		return redirect(reverse('mural_area', args=[areas.first().id]))
	if areas.exists():
		return render(request, 'mural/eleccion_areas.html', {'areas': areas})
	return redirect(reverse('mural_principal'))

