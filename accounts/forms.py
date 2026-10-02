from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import User

# Class CSS-nya ada di wiji.css
INPUT_CLASS = 'field-input'


class InvalidFieldMixin:
    """Isi form salah"""

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs['class'] = f"{attrs.get('class', '')} is-invalid".strip()
                attrs['aria-invalid'] = 'true'


class LoginForm(InvalidFieldMixin, AuthenticationForm):
    """Form masuk"""

    error_messages = {
        'invalid_login': 'Nama pengguna atau kata sandi salah. Coba lagi.',
        'inactive': 'Akun ini tidak aktif.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nama pengguna'
        self.fields['username'].widget.attrs.update(
            {'class': INPUT_CLASS, 'autocomplete': 'username', 'autofocus': True}
        )
        self.fields['password'].label = 'Kata sandi'
        self.fields['password'].widget.attrs.update(
            {'class': INPUT_CLASS, 'autocomplete': 'current-password'}
        )


class OwnerRegistrationForm(InvalidFieldMixin, forms.ModelForm):
    """Registrasi publik, Pemilik lahan"""

    password1 = forms.CharField(
        label='Kata sandi',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Ulangi kata sandi',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email')
        labels = {
            'first_name': 'Nama lengkap',
            'username': 'Nama pengguna',
            'email': 'Email',
        }
        error_messages = {
            'username': {'unique': 'Nama pengguna ini sudah dipakai.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        self.fields['username'].help_text = ''
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', INPUT_CLASS)
        self.fields['first_name'].widget.attrs['autocomplete'] = 'name'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['password1'].help_text = 'Minimal 8 karakter, campuran huruf dan angka.'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email ini sudah terdaftar.')
        return email

    def clean_password1(self):
        password = self.cleaned_data['password1']
        # Tambahan dari kita: password harus ada huruf dan angka
        if not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            raise forms.ValidationError('Kata sandi harus berisi huruf dan angka.')
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Kata sandi tidak sama.')
        elif password1:
            candidate = User(
                username=cleaned.get('username', ''),
                email=cleaned.get('email', ''),
                first_name=cleaned.get('first_name', ''),
            )
            try:
                password_validation.validate_password(password1, candidate)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.OWNER
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
