import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from operatividad.models import Area, Contenido, Archivo as ArchivoModel, AreaDestinatario, AsignacionArea
from .forms import ContenidoForm

logger = logging.getLogger(__name__)

# --- APIS PÚBLICAS ---
def api_areas(request):
    return JsonResponse({
        'U': list(Area.objects.filter(nivel_formacion=Area.NIVEL_U).values('id', 'nombre')),
        'IP': list(Area.objects.filter(nivel_formacion=Area.NIVEL_IP).values('id', 'nombre')),
        'CFT': list(Area.objects.filter(nivel_formacion=Area.NIVEL_CFT).values('id', 'nombre')),
        'GEN': list(Area.objects.filter(nivel_formacion=Area.NIVEL_GEN).values('id', 'nombre')),
    })

def api_contenidos(request, area_id):
    area = get_object_or_404(Area, pk=area_id)
    contenidos_qs = Contenido.objects.filter(
        destinatarios__area=area, 
        destinatarios__estado=AreaDestinatario.ESTADO_PUBLICADO
    ).distinct().order_by('-fecha_creacion')
    
    lista = []
    for c in contenidos_qs:
        archivos_data = []
        imagen_url = ""
        
        # Recorremos todos los archivos adjuntos de este contenido
        for a in c.archivos.all():
            if not a.ruta_archivo: 
                continue
                
            url_completa = request.build_absolute_uri(a.ruta_archivo.url)
            nombre_archivo = a.ruta_archivo.name.split('/')[-1] # Obtener solo el nombre, sin la ruta
            
            # Si el archivo termina en extensión de imagen y aún no tenemos imagen_url, lo asignamos
            if not imagen_url and url_completa.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                imagen_url = url_completa
                
            # Guardamos todos los archivos (imágenes, pdfs, etc.) en una lista
            archivos_data.append({
                'id': a.id,
                'nombre': nombre_archivo,
                'url': url_completa
            })

        lista.append({
            'id': c.id, 
            'titulo': c.titulo, 
            'contenido': c.contenido,
            'imagen_url': imagen_url,
            'archivos': archivos_data, # <--- ¡Enviamos todos los archivos a React!
            'color': c.color, 
            'tipo_contenido': c.tipo_contenido,
            'fecha': c.fecha_creacion.strftime('%d/%m/%Y %H:%M')
        })
        
    return JsonResponse({'area_nombre': area.nombre, 'contenidos': lista})

def vista_react(request, area_id=None):
    return render(request, 'mural/mural_react.html')

# --- HELPERS INTERNOS ---
def _areas_permitidas_para_usuario(usuario):
    if usuario.is_superuser: return Area.objects.all()
    return Area.objects.filter(asignaciones__usuario=usuario).distinct()

def _es_dae(usuario):
    if usuario.is_superuser: return True
    return Area.objects.filter(asignaciones__usuario=usuario, nivel_formacion=Area.NIVEL_GEN).exists()

def _user_default_area(user, allowed_areas):
    asignacion = AsignacionArea.objects.filter(usuario=user).select_related('area').order_by('rol').first()
    if asignacion and asignacion.area: return asignacion.area
    return allowed_areas.first() if allowed_areas.exists() else None

def _sync_publication_states():
    now = timezone.now()
    AreaDestinatario.objects.filter(estado=AreaDestinatario.ESTADO_EN_ESPERA, fecha_asignacion__lte=now).update(estado=AreaDestinatario.ESTADO_PUBLICADO)
    AreaDestinatario.objects.filter(fecha_limite__lt=now, estado=AreaDestinatario.ESTADO_PUBLICADO).update(estado=AreaDestinatario.ESTADO_BORRADOR, fecha_asignacion=now)

# --- VISTAS DEL PANEL ---
@login_required
def contenidos_mis_areas(request):
    _sync_publication_states()
    user = request.user
    areas_permitidas = _areas_permitidas_para_usuario(user)

    # 1. GESTIÓN DE PERFIL Y USUARIOS
    profile_role = None
    asig = AsignacionArea.objects.filter(usuario=user).select_related('area').first()
    if asig:
        profile_role = asig.rol

    can_manage_users = user.is_superuser or AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_JEFE).exists()
    
    users_list = []
    all_areas = []
    User = get_user_model()
    if can_manage_users:
        if user.is_superuser:
            users_qs = User.objects.all()
            all_areas = list(Area.objects.all().order_by('nombre'))
        else:
            users_qs = User.objects.filter(asignaciones_area__area__in=areas_permitidas).distinct()
            all_areas = list(areas_permitidas.order_by('nombre'))
            
        for u in users_qs.order_by('first_name', 'last_name'):
            u_areas = Area.objects.filter(asignaciones__usuario=u).distinct()
            rol_obj = AsignacionArea.objects.filter(usuario=u, area__in=areas_permitidas).first()
            users_list.append({
                'id': u.id, 
                'nombre': u.get_full_name() or u.username, 
                'email': u.email, 
                'areas': [a.nombre for a in u_areas], 
                'areas_ids': [a.id for a in u_areas], 
                'role': 'Administrador' if u.is_superuser else (rol_obj.rol if rol_obj else '')
            })

    # 2. GESTIÓN DE CONTENIDOS
    if user.is_superuser:
        contenidos = Contenido.objects.all()
    else:
        contenidos = Contenido.objects.filter(destinatarios__area__in=areas_permitidas).distinct()

    filtro_estado = request.GET.get('estado')
    if filtro_estado and filtro_estado != AreaDestinatario.ESTADO_PUBLICADO:
        contenidos = contenidos.filter(destinatarios__estado=filtro_estado).distinct()

    selected_area = request.GET.get('area')
    if selected_area and selected_area.isdigit():
        contenidos = contenidos.filter(destinatarios__area__id=selected_area).distinct()

    contenidos_list = list(contenidos.order_by('-fecha_creacion'))
    for c in contenidos_list:
        dest_states = list(c.destinatarios.values_list('estado', flat=True))
        if AreaDestinatario.ESTADO_PUBLICADO in dest_states:
            c.computed_estado = AreaDestinatario.ESTADO_PUBLICADO
        elif AreaDestinatario.ESTADO_EN_ESPERA in dest_states:
            c.computed_estado = AreaDestinatario.ESTADO_EN_ESPERA
        else:
            c.computed_estado = AreaDestinatario.ESTADO_BORRADOR
        c.can_edit = True if user.is_superuser else c.destinatarios.filter(area__in=areas_permitidas).exists()
        c.has_any_published = c.destinatarios.filter(estado=AreaDestinatario.ESTADO_PUBLICADO).exists()

    form = ContenidoForm(user=user)
    area_default = _user_default_area(user, areas_permitidas)

    return render(request, 'operatividad/gest_contenidos.html', {
        'contenidos': contenidos_list,
        'form': form,
        'accion': 'Crear',
        'filter_areas': areas_permitidas.order_by('nombre'),
        'selected_area': int(selected_area) if selected_area and selected_area.isdigit() else None,
        'can_choose_levels': _es_dae(user),
        'default_area_id': area_default.id if area_default else None,
        
        # ¡VARIABLES RESTAURADAS!
        'filter_estado': filtro_estado, 
        'profile_role': profile_role,   
        'can_manage_users': can_manage_users, 
        'users_list': users_list,       
        'all_areas': all_areas,         
    })


@login_required
def contenido_crear(request):
    if request.method != 'POST': return redirect('contenidos_mis_areas')
    
    user = request.user
    allowed_areas = _areas_permitidas_para_usuario(user)
    form = ContenidoForm(request.POST, user=user)

    if form.is_valid():
        accion = request.POST.getlist('accion')[-1] if request.POST.getlist('accion') else 'borrador'
        contenido = form.save()
        
        tipo_contenido = form.cleaned_data.get('tipo_contenido')

        # Procesamiento y validación de archivos
        for f in request.FILES.getlist('archivo_adjunto'):
            ext = f.name.split('.')[-1].lower()
            # Validación CRÍTICA para alertas
            if tipo_contenido == Contenido.TIPO_ALERTA:
                if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                    messages.warning(request, f"El archivo '{f.name}' fue omitido. Las Alertas solo permiten imágenes (JPG, PNG, WEBP).")
                    continue # Saltamos este archivo y no lo guardamos
            
            ArchivoModel.objects.create(contenido=contenido, ruta_archivo=f)

        now = timezone.now()
        scheduled = form.cleaned_data.get('fecha_publicacion_programada')
        fecha_limite = form.cleaned_data.get('fecha_limite')
        
        niveles = form.cleaned_data.get('niveles_destino') or []
        destinos = list(Area.objects.filter(nivel_formacion__in=niveles)) if niveles else list(form.cleaned_data.get('destinatarios') or [])        
        
        if not user.is_superuser and not allowed_areas.filter(nivel_formacion=Area.NIVEL_GEN).exists():
            destinos = [d for d in destinos if d in allowed_areas]

        for area_dest in destinos:
            estado_target = AreaDestinatario.ESTADO_BORRADOR
            if accion == 'publicar':
                estado_target = AreaDestinatario.ESTADO_EN_ESPERA if (scheduled and scheduled > now) else AreaDestinatario.ESTADO_PUBLICADO

            AreaDestinatario.objects.create(
                area=area_dest, contenido=contenido,
                estado=estado_target, fecha_limite=fecha_limite, fecha_asignacion=scheduled or now
            )

        messages.success(request, 'Contenido creado exitosamente.')
        return redirect('contenidos_mis_areas')

    for error in form.errors.values(): messages.error(request, error)
    return redirect('contenidos_mis_areas')

@login_required
def contenido_editar(request, pk):
    contenido = get_object_or_404(Contenido, pk=pk)
    user = request.user
    allowed_areas = _areas_permitidas_para_usuario(user)

    # --- 1. LÓGICA DE GUARDADO (POST) ---
    if request.method == 'POST':
        form = ContenidoForm(request.POST, instance=contenido, user=user)
        if form.is_valid():
            accion = request.POST.get('accion', 'borrador')
            contenido_editado = form.save()
            tipo_contenido = form.cleaned_data.get('tipo_contenido')

            # Eliminar archivos seleccionados para borrado
            remove_ids = [int(x) for x in request.POST.getlist('remove_archivos') if x]
            if remove_ids:
                ArchivoModel.objects.filter(id__in=remove_ids, contenido=contenido_editado).delete()

            # Procesamiento y validación de nuevos archivos
            for f in request.FILES.getlist('archivo_adjunto'):
                ext = f.name.split('.')[-1].lower()
                # Validación CRÍTICA para alertas
                if tipo_contenido == Contenido.TIPO_ALERTA:
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        messages.warning(request, f"El archivo '{f.name}' fue omitido. Las Alertas solo permiten imágenes (JPG, PNG, WEBP).")
                        continue # Saltamos este archivo y no lo guardamos
                        
                ArchivoModel.objects.create(contenido=contenido_editado, ruta_archivo=f)

            # Leemos los niveles (U, IP, CFT) O las áreas específicas
            niveles = form.cleaned_data.get('niveles_destino') or []
            destinos = list(Area.objects.filter(nivel_formacion__in=niveles)) if niveles else list(form.cleaned_data.get('destinatarios') or [])

            if not _es_dae(user) and not user.is_superuser:
                destinos = [d for d in destinos if d in allowed_areas]
                existentes = set(contenido.destinatarios.values_list('area_id', flat=True))
                intocables = existentes - set(allowed_areas.values_list('id', flat=True))
                destinos.extend(list(Area.objects.filter(id__in=intocables)))

            new_ids = set([d.id for d in destinos])
            AreaDestinatario.objects.filter(contenido=contenido_editado).exclude(area_id__in=new_ids).delete()

            now = timezone.now()
            scheduled = form.cleaned_data.get('fecha_publicacion_programada')
            fecha_limite = form.cleaned_data.get('fecha_limite')

            for area_dest in destinos:
                estado_target = AreaDestinatario.ESTADO_BORRADOR
                if accion == 'publicar':
                    estado_target = AreaDestinatario.ESTADO_EN_ESPERA if (scheduled and scheduled > now) else AreaDestinatario.ESTADO_PUBLICADO

                AreaDestinatario.objects.update_or_create(
                    area=area_dest, contenido=contenido_editado,
                    defaults={'estado': estado_target, 'fecha_limite': fecha_limite, 'fecha_asignacion': scheduled or now}
                )

            messages.success(request, 'Contenido actualizado correctamente.')
            return redirect('contenidos_mis_areas')
            
        for error in form.errors.values():
            messages.error(request, error)
        return redirect('contenidos_mis_areas')

@login_required
def contenido_eliminar(request, pk):
    if request.method == 'POST':
        contenido = get_object_or_404(Contenido, pk=pk)
        if request.user.is_superuser:
            contenido.delete()
        else:
            allowed_areas = _areas_permitidas_para_usuario(request.user)
            intersect = set(allowed_areas.values_list('id', flat=True)) & set(contenido.destinatarios.values_list('area_id', flat=True))
            if intersect:
                AreaDestinatario.objects.filter(contenido=contenido, area_id__in=list(intersect)).delete()
    return redirect('contenidos_mis_areas')

@login_required
def ir_a_mis_areas(request):
    return redirect(reverse('index'))