from django.urls import path

from regras import views

urlpatterns = [
    path('', views.configurar_regras, name='regras_config'),
]
