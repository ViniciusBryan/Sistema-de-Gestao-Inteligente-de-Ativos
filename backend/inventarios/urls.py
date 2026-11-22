from django.urls import path

from inventarios import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('inventarios/', views.listar_inventarios, name='inventario_list'),
    path('inventarios/<uuid:inventario_id>/', views.auditar_inventario, name='inventario_auditar'),
]
