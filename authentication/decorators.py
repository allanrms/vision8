from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def finance_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'finance':
            messages.error(request, 'Você não tem permissão para acessar esta área.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper


def attendant_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'attendant':
            messages.error(request, 'Você não tem permissão para acessar esta área.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper