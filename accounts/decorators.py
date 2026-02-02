from django.contrib.auth.decorators import user_passes_test

def teacher_required(view_func):
    decorator = user_passes_test(lambda u: u.groups.filter(name='Teacher').exists())
    return decorator(view_func)

def finance_required(view_func):
    decorator = user_passes_test(lambda u: u.groups.filter(name='Finance').exists() or u.groups.filter(name='Principal').exists())
    return decorator(view_func)

def principal_required(view_func):
    decorator = user_passes_test(lambda u: u.groups.filter(name='Principal').exists())
    return decorator(view_func)