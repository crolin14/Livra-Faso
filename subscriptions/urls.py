from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.subscription_plans, name='plans'),
    path('list/', views.plan_list, name='plan_list'),
    path('subscribe/<int:plan_id>/', views.subscribe, name='subscribe'),
    path('payment/<int:subscription_id>/', views.payment, name='payment'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('confirm-bank-transfer/', views.confirm_bank_transfer, name='confirm_bank_transfer'),
    path('history/', views.payment_history, name='history'),
    path('cancel/<int:subscription_id>/', views.cancel_subscription, name='cancel'),
] 