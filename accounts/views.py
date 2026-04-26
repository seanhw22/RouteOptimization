"""Views for the accounts app: registration, login, logout, guest landing."""

from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, EmailRegistrationForm


class EmailLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user, backend='accounts.backends.EmailBackend')
        self.request.session.pop('is_guest', None)
        return redirect(self.get_success_url())


class EmailLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('datasets:list')

    if request.method == 'POST':
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.pop('is_guest', None)
            return redirect('datasets:list')
    else:
        form = EmailRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def continue_as_guest(request):
    """Mark the session as a guest session and forward to dataset upload."""
    request.session['is_guest'] = True
    request.session.setdefault('guest_datasets', [])
    if not request.session.session_key:
        request.session.create()
    return redirect('datasets:upload')
