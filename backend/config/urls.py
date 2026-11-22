"""
Roteamento principal do SIGA Web Admin (v1.0) delegando cada módulo ao seu app.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inventarios.urls')),
    path('', include('empresas.urls')),
    path('ativos/', include('ativos.urls')),
    path('regras/', include('regras.urls')),
    path('dispositivos/', include('dispositivos.urls')),
    path('api/', include('api_mobile.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
