from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:wallet_id>', views.wallet, name='wallet'),
    path('token/<int:token_id>', views.tokens, name='tokens'),
]