# accounts/context_processors.py
from django.urls import reverse

def dashboard_info(request):
    dashboard_url = reverse('login')  # fallback
    user_role = None

    if request.user.is_authenticated:
        # Check which group the user belongs to
        groups = request.user.groups.values_list('name', flat=True)
        if 'Principal' in groups:
            dashboard_url = reverse('principal_dashboard')
            user_role = 'Principal'
        elif 'Finance' in groups:
            dashboard_url = reverse('finance_dashboard')
            user_role = 'Finance'
        elif 'Teacher' in groups:
            dashboard_url = reverse('teacher_dashboard')
            user_role = 'Teacher'

    return {
        'dashboard_url': dashboard_url,
        'user_role': user_role
    }
