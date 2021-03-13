from django.urls import path
from django.conf.urls import include, url

from . import views

app_name = 'chat'

urlpatterns = [
	path('', views.index, name='index'),
	path('base', views.base, name='base'),
	path('<str:room_name>/', views.room, name='room'),

 	url(r"^accounts/", include("django.contrib.auth.urls")),
    url(r"^register/", views.register, name="register"),   
]