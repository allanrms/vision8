from django.shortcuts import redirect
from django.urls import reverse


class RoleBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'role'):
            path = request.path

            if request.user.role == 'finance':
                if path == '/' or path.startswith('/webapp'):
                    return redirect('/finance/')

            elif request.user.role == 'attendant':
                if path == '/' or path.startswith('/finance'):
                    return redirect('/webapp/')

        response = self.get_response(request)
        return response