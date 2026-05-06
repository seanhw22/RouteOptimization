"""Views for the accounts app: registration, login, logout, guest landing."""

from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, EmailRegistrationForm


def _claim_guest_data(user, guest_dataset_ids, old_session_key):
    """Transfer guest datasets and run batches to a newly authenticated user."""
    from datasets.models import Dataset
    from runs.models import RunBatch

    if guest_dataset_ids:
        Dataset.objects.filter(pk__in=guest_dataset_ids).update(
            user=user, session_key='', expires_at=None
        )
    if old_session_key:
        RunBatch.objects.filter(session_key=old_session_key, user__isnull=True).update(
            user=user, session_key=''
        )


class EmailLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        guest_dataset_ids = list(self.request.session.get('guest_datasets', []))
        old_session_key = self.request.session.session_key
        user = form.get_user()
        login(self.request, user, backend='accounts.backends.EmailBackend')
        self.request.session.pop('is_guest', None)
        _claim_guest_data(user, guest_dataset_ids, old_session_key)
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
            guest_dataset_ids = list(request.session.get('guest_datasets', []))
            old_session_key = request.session.session_key
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.pop('is_guest', None)
            _claim_guest_data(user, guest_dataset_ids, old_session_key)
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
