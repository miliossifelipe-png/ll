from django.urls import path
from . import views
 
urlpatterns = [
    path('', views.channel_list, name='channel_list'),
    path('novo/', views.channel_create, name='channel_create'),
    path('<int:pk>/editar/', views.channel_edit, name='channel_edit'),
    path('<int:pk>/deletar/', views.channel_delete, name='channel_delete'),
] 