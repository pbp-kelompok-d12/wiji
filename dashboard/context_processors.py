from django.utils.functional import SimpleLazyObject

from .lahan import RingkasanLahan


def sidebar(request):
    """Angka lahan buat sidebar pemilik. Dibikin lazy, jadi halaman yang nggak memakainya nggak kena query."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or user.is_staff or not user.is_owner:
        return {}
    return {'sidebar_lahan': SimpleLazyObject(lambda: RingkasanLahan(user))}
