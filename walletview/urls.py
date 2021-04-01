from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path('',login_required(views.IndexView.as_view()), name='home'),
    path('wallets',login_required(views.IndexView.as_view()) , name='wallets'),
    path('wallets/add',views.add_wallet , name='add_wallet'),
    path('wallets/<wallet_address>', views.wallet, name='wallet'),
    path('token/<int:token_id>', views.tokens, name='tokens'),
]