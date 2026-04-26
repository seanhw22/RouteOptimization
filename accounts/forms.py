"""Forms for the accounts app: email-based registration."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('That email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Use the email as the username so Django auth keeps working
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(forms.Form):
    """Login by email + password (mirrors AuthenticationForm but accepts email)."""

    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': 'Invalid email or password.',
        'inactive': 'This account is inactive.',
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        from django.contrib.auth import authenticate

        email = (self.cleaned_data.get('email') or '').strip().lower()
        password = self.cleaned_data.get('password')
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError(self.error_messages['invalid_login'])
            if not user.is_active:
                raise forms.ValidationError(self.error_messages['inactive'])
            self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
