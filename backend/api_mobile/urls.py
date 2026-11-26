from django.urls import path

from api_mobile import views

urlpatterns = [
    path('login/', views.LoginMobileAPIView.as_view(), name='api_login'),
    path('sincronizar/', views.SincronizacaoAPIView.as_view(), name='api_sincronizar'),
    path('catalogo/', views.CatalogoAtivosAPIView.as_view(), name='api_catalogo'),
    path('regras/', views.RegraOperacionalMobileAPIView.as_view(), name='api_regras'),
]
