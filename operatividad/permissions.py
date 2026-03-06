from typing import Optional
from django.contrib.auth import get_user_model
from .models import AsignacionArea, Area, Contenido

User = get_user_model()


def _roles_for_user_in_area(user: User, area: Area):
    """Return a set of role names the user has in the given area."""
    if user is None or not user.is_authenticated:
        return set()
    qs = AsignacionArea.objects.filter(usuario=user, area=area)
    return set(a.rol for a in qs)


def is_system_admin(user: User) -> bool:
    """True if user has system administrator role anywhere or is superuser."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    # Administrador role assigned in any area counts as system admin
    return AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_ADMIN).exists()


def is_jefe_de_area(user: User, area: Optional[Area] = None) -> bool:
    """True if user is jefe for the given area (or any area if area is None)."""
    if not user or not user.is_authenticated:
        return False
    if area is None:
        return AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_JEFE).exists()
    return AsignacionArea.objects.filter(usuario=user, area=area, rol=AsignacionArea.ROL_JEFE).exists()


def is_editor(user: User, area: Optional[Area] = None) -> bool:
    """True if user is editor in given area or anywhere if area is None."""
    if not user or not user.is_authenticated:
        return False
    if area is None:
        return AsignacionArea.objects.filter(usuario=user, rol=AsignacionArea.ROL_EDITOR).exists()
    return AsignacionArea.objects.filter(usuario=user, area=area, rol=AsignacionArea.ROL_EDITOR).exists()


def can_manage_content(user: User, area: Area) -> bool:
    """Return True if user may create/edit content for `area`.

    Rules implemented:
    - System admins may manage any content.
    - Jefes may manage content in areas they are jefe of and may manage content
      related to areas they administrate.
    - Editors may manage content only in areas they are assigned to as editor.
    """
    if is_system_admin(user):
        return True
    if is_jefe_de_area(user, area):
        return True
    if is_editor(user, area):
        return True
    return False


def can_create_user_with_role(creator: User, target_role: str, target_area: Optional[Area] = None) -> bool:
    """Return True if `creator` may create a user assigned `target_role` in `target_area`.

    Rules implemented:
    - System admins can create users of any role anywhere.
    - Jefes can create users with the same role as themselves or lower (editor)
      for areas they are jefe of. They can also create editors or jefes within their area.
    - Editors cannot create users.
    """
    if is_system_admin(creator):
        return True
    # Editors cannot create users
    if target_role == AsignacionArea.ROL_EDITOR:
        # only admins or jefes for that area can create editors
        return is_jefe_de_area(creator, target_area)
    if target_role == AsignacionArea.ROL_JEFE:
        # only system admins can create another jefe globally
        return False
    if target_role == AsignacionArea.ROL_ADMIN:
        # only system admins
        return False
    return False


def can_publish_from_to(from_area: Area, to_area: Area) -> bool:
    """Return True if content created in `from_area` may be published to `to_area`.

    Business rule implemented:
    - Areas with nivel_formacion == 'GEN' (general) can publish to other areas.
    - Other areas can publish only to themselves.
    """
    if from_area.id == to_area.id:
        return True
    if from_area.nivel_formacion == Area.NIVEL_GEN:
        return True
    return False


def user_can_publish_content(user: User, contenido: Contenido, target_area: Area) -> bool:
    """Return True if `user` may publish `contenido` (whose area_origen is used)
    to `target_area` following role rules and area-level rules.
    """
    # Only users who can manage content in the origin area can publish
    origin = contenido.area_origen
    if not can_manage_content(user, origin):
        return False
    # And publishing target must be allowed by area-level rule
    return can_publish_from_to(origin, target_area)
