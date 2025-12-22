from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from apps.m3u.models import M3UAccount
import json


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class M3UDashboardView(View):
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests for the M3U dashboard.
        Renders the m3u.html template with M3U account data.
        """
        m3u_accounts = M3UAccount.objects.all()
        return render(request, 'm3u/m3u.html', {'m3u_accounts': m3u_accounts})

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to create a new M3U account.
        Expects JSON data in the request body.
        """
        try:
            data = json.loads(request.body)
            new_account = M3UAccount.objects.create(**data)
            return JsonResponse({
                'id': new_account.id,
                'message': 'M3U account created successfully!'
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
