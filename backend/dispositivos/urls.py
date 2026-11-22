from django.urls import path

from dispositivos import views

urlpatterns = [
    path('', views.listar_dispositivos, name='dispositivo_list'),
    path('<uuid:pk>/status/', views.alternar_status_dispositivo, name='dispositivo_status'),
]
