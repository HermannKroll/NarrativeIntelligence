from django.conf import settings

def version_tag(request):
    return {'v_tag': settings.STATIC_VERSION}
