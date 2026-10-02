from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .forms import LoginForm, OwnerRegistrationForm
from .models import User


class WijiLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class WijiLogoutView(LogoutView):
    """Django 5 cuma bolehin logout lewat POST."""

    def post(self, request, *args, **kwargs):
        messages.success(request, 'Kamu sudah keluar.')
        return super().post(request, *args, **kwargs)


def register(request):
    if request.user.is_authenticated:
        return redirect('core:landing')

    form = OwnerRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Selamat datang di Wiji, {user.display_name}!')
        return redirect('core:landing')
    return render(request, 'accounts/register.html', {'form': form})


@require_GET
def check_username(request):
    """Dipanggil HTMX buat ngecek username udah dipakai atau belum."""
    username = request.GET.get('username', '').strip()
    available = None
    if username:
        available = not User.objects.filter(username__iexact=username).exists()
    return render(request, 'accounts/partials/username_status.html', {'available': available})
