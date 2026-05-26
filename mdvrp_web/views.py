"""Views for the project-level pages (homepage, etc.)."""

from django.shortcuts import render


def homepage(request):
    return render(request, 'home.html')
