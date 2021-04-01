from walletview.helper import blockscout
from django.conf.urls import url
from django.views import generic
from django import template
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Wallet, WatchWallet, format_money
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

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        total = 0.0
        for wallet in context['wallets']:
            total += wallet.wallet.value()
        context['total'] = format_money(total)
        return context

@login_required
def wallet(request, wallet_id):
    wallet = get_object_or_404(Wallet, pk=wallet_id)
    return render(request, 'walletview/wallet.html', {'wallet': wallet})

@login_required
def add_wallet(request):
    if request.method == "POST":
        name = request.POST.get("name")
        wallet = request.POST.get("wallet").lower()
        if blockscout.fetch_wallet_balance(wallet) is not None:
            (wallet,created_wallet) = Wallet.objects.get_or_create(address=wallet,verified=True)
            (watch,_) = WatchWallet.objects.get_or_create(user=request.user,wallet=wallet,name=name)
            if created_wallet:
                wallet.update()
    return redirect("wallets")


def tokens(request, token_id):
    response = "You're looking at the token %s."
    return HttpResponse(response % token_id)

