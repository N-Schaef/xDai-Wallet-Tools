from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('<int:wallet_id>', views.wallet, name='wallet'),
    path('token/<int:token_id>', views.tokens, name='tokens'),
]