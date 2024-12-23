from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('exportar/', views.exportar, name='exportar'),  # Defina a URL exportar
    path('login/', views.login_view, name='login'),  # URL de login
    path('logout/', views.logout_view, name='logout'),  # Adiciona a URL para o logoff

]