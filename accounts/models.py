from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Admin pakai is_staff, jadi nggak ada role admin."""

    class Role(models.TextChoices):
        OWNER = 'owner', 'Pemilik Lahan'
        OFFICER = 'officer', 'Petugas Pemeriksa'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_officer(self):
        return self.role == self.Role.OFFICER

    @property
    def role_label(self):
        """Nama peran buat ditampilkan. Admin itu akun staf, kolom role-nya nggak dipakai."""
        return 'Admin' if self.is_staff else self.get_role_display()

    @property
    def initials(self):
        parts = self.display_name.split()
        return ''.join(p[0] for p in parts[:2]).upper() or '?'

    @property
    def display_name(self):
        return self.get_full_name() or self.username
