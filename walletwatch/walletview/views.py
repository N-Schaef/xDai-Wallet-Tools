from django.views import generic
from django import template
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Wallet, WatchWallet
# Create your views here.

def home(request):
    return render(request, 'home.html')


class IndexView(generic.ListView):
    template_name = 'walletview/index.html'
    context_object_name = 'wallets'

    def get_queryset(self):
        """Return all wallets watched by the user"""
        wallets=WatchWallet.objects.prefetch_related('wallet').filter(user=self.request.user)
        return wallets


def wallet(request, wallet_id):
    wallet = get_object_or_404(Wallet, pk=wallet_id)
    return render(request, 'walletview/wallet.html', {'wallet': wallet})





def tokens(request, token_id):
    response = "You're looking at the token %s."
    return HttpResponse(response % token_id)

