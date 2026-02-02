from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('dashboard/', views.conversation_list, name='dashboard_list'),
    path('', views.conversation_list, name='list'),
    path('<int:conversation_id>/', views.conversation_detail, name='detail'),
    path('<int:conversation_id>/send/', views.send_message, name='send'),
    path('start/<int:user_id>/', views.start_conversation, name='start'),
] 