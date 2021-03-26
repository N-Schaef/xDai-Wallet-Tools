from django.views import generic
from django import template
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, render
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


def tokens(request, token_id):
    response = "You're looking at the token %s."
    return HttpResponse(response % token_id)

