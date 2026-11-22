from django.urls import path

from empresas import views

urlpatterns = [
    path('login/', views.entrar, name='login'),
    path('logout/', views.sair, name='logout'),
    path('cadastro-empresa/', views.cadastrar_empresa, name='cadastro_empresa'),
    path('usuarios/', views.listar_usuarios, name='usuario_list'),
    path('usuarios/novo/', views.adicionar_usuario, name='usuario_novo'),
    path('usuarios/<uuid:pk>/status/', views.alternar_status_usuario, name='usuario_status'),
]
