from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:id>', views.container),
    path('<str:id>/stop', views.stop),
    path('<str:id>/start', views.start),
    path('<str:id>/restart', views.restart),
    path('<str:id>/logs', views.logs),
]