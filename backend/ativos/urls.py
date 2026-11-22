from django.urls import path

from ativos import views

urlpatterns = [
    path('', views.listar_ativos, name='ativo_list'),
    path('novo/', views.adicionar_ativo, name='ativo_novo'),
    path('<int:pk>/editar/', views.editar_ativo, name='ativo_editar'),
]
