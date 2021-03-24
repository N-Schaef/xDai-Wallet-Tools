from django import template
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, render
from .models import Wallet
# Create your views here.
def index(request):
    user_wallets = Wallet.objects.all()
    context = {
        'user_wallets': user_wallets,
    }
    return render(request, 'walletview/index.html', context)

def tokens(request, token_id):
    response = "You're looking at the token %s."
    return HttpResponse(response % token_id)

def wallet(request, wallet_id):
    wallet = get_object_or_404(Wallet, pk=wallet_id)
    return render(request, 'walletview/wallet.html', {'wallet': wallet})
