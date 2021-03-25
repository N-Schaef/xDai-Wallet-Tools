from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('wallets', views.IndexView.as_view(), name='wallets'),
    path('<int:wallet_id>', views.wallet, name='wallet'),
    path('token/<int:token_id>', views.tokens, name='tokens'),
]