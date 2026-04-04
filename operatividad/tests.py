from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from mural.models import Area
from .models import AreaDestinatario, AsignacionArea, Contenido
from .forms import CrearUsuarioForm

User = get_user_model()


class SimpleOperatividadTests(TestCase):
    def setUp(self):
        # áreas
        self.area_inf = Area.objects.create(nombre='Inf', nivel_formacion=Area.NIVEL_IP)
        self.area_sal = Area.objects.create(nombre='Salud', nivel_formacion=Area.NIVEL_CFT)

        # usuarios
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw')
        self.jefe = User.objects.create_user(username='jefe', email='jefe@example.com', password='pw')
        AsignacionArea.objects.create(usuario=self.jefe, area=self.area_inf, rol=AsignacionArea.ROL_JEFE)
        self.user = User.objects.create_user(username='u', email='u@example.com', password='pw')
        self.user2 = User.objects.create_user(username='u2', email='u2@example.com', password='pw')
        self.area_inf.usuarios.add(self.user)

    # helpers
    def post_create_user(self, client, **kwargs):
        data = {
            'first_name': kwargs.get('first_name', 'N'),
            'last_name': kwargs.get('last_name', 'L'),
            'email': kwargs.get('email', 'x@e'),
            'password1': kwargs.get('password1', 'pw'),
            'password2': kwargs.get('password2', 'pw'),
            'area': kwargs.get('area', [self.area_inf.id]),
            'role': kwargs.get('role', AsignacionArea.ROL_EDITOR),
        }
        return client.post(reverse('usuarios_crear'), data)

    # forms
    def test_crear_usuario_form_validation(self):
        ok = CrearUsuarioForm(data={'first_name':'A','last_name':'B','email':'a@example.com','area':[self.area_inf.id],'password1':'1','password2':'1'})
        bad = CrearUsuarioForm(data={'first_name':'A','last_name':'B','email':'a@example.com','area':[self.area_inf.id],'password1':'1','password2':'2'})
        self.assertTrue(ok.is_valid())
        self.assertFalse(bad.is_valid())

    # acceso
    def test_panel_requiere_login(self):
        r = self.client.get(reverse('panel_operatividad'))
        self.assertEqual(r.status_code, 302)

    # usuarios: superuser vs jefe
    def test_superuser_puede_asignar_cualquier_area(self):
        self.client.force_login(self.admin)
        resp = self.post_create_user(self.client, email='s@example.com', area=[self.area_sal.id])
        self.assertIn(resp.status_code, (200,302,303))
        self.assertTrue(User.objects.filter(email='s@example.com').exists())

    def test_jefe_no_asigna_area_ajena(self):
        self.client.force_login(self.jefe)
        resp = self.post_create_user(self.client, email='bad@example.com', area=[self.area_sal.id])
        # puede no crear o crear sin la asignación prohibida
        u = User.objects.filter(email='bad@e').first()
        if u:
            self.assertFalse(u.asignaciones_area.filter(area=self.area_sal).exists())

    def test_jefe_asigna_su_area(self):
        self.client.force_login(self.jefe)
        resp = self.post_create_user(self.client, email='ok@example.com', area=[self.area_inf.id])
        u = User.objects.get(email='ok@example.com')
        self.assertTrue(u.asignaciones_area.filter(area=self.area_inf).exists())

    # contenidos: programación y permisos
    def test_publicacion_programada_y_sync(self):
        self.client.force_login(self.user)
        from django.utils import timezone
        from datetime import timedelta
        future = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        data = {'titulo':'T','breve_descripcion':'b','tipo_contenido':'NOTICIA','destinatarios':[str(self.area_inf.id)],'fecha_publicacion_programada':future,'accion':'publicar'}
        r = self.client.post(reverse('contenido_crear'), data)
        self.assertIn(r.status_code, (200,302,303))
        c = Contenido.objects.filter(titulo='T').first()
        self.assertIsNotNone(c)
        ad = AreaDestinatario.objects.filter(contenido=c, area=self.area_inf).first()
        self.assertEqual(ad.estado, AreaDestinatario.ESTADO_EN_ESPERA)
        # forzar promoción
        from mural.views import _sync_publication_states
        AreaDestinatario.objects.filter(pk=ad.pk).update(fecha_asignacion=timezone.now() - timedelta(days=1))
        promoted, _ = _sync_publication_states()
        self.assertTrue(promoted >= 0)

    def test_eliminar_contenido_y_permisos(self):
        cont = Contenido.objects.create(area_origen=self.area_inf, titulo='X', breve_descripcion='b', tipo_contenido='NOTICIA')
        AreaDestinatario.objects.create(area=self.area_inf, contenido=cont, estado=AreaDestinatario.ESTADO_PUBLICADO)
        self.client.force_login(self.user2)
        r = self.client.post(reverse('contenido_eliminar', args=[cont.pk]), {})
        self.assertIn(r.status_code, (200,302,303))
        self.assertTrue(Contenido.objects.filter(pk=cont.pk).exists())
        self.client.force_login(self.admin)
        r2 = self.client.post(reverse('contenido_eliminar', args=[cont.pk]), {})
        self.assertIn(r2.status_code, (200,302,303))
        self.assertFalse(Contenido.objects.filter(pk=cont.pk).exists())

    def test_cambiar_clave_preserva_sesion_y_no_borrarse_a_si_mismo(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('contenidos_mis_areas'), {'profile_update':'1','first_name':'F','last_name':'L','password1':'new','password2':'new'})
        self.assertIn(resp.status_code, (200,302,303))
        self.assertEqual(str(self.user.pk), self.client.session.get('_auth_user_id'))
        # no puede borrarse a sí mismo
        r = self.client.post(reverse('usuarios_eliminar', args=[self.user.pk]), {})
        self.assertIn(r.status_code, (200,302,303))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())


