import json
from walletview.helper import blockscout
from django.conf.urls import url
from django.views import generic
from django import template
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import LiquidityToken, Token, Wallet, WatchWallet, get_best_priced
from django.utils.safestring import mark_safe
# Create your views here.


def home(request):
    return render(request, 'home.html')


class IndexView(generic.ListView):
    template_name = 'walletview/index.html'
    context_object_name = 'wallets'

    def get_queryset(self):
        """Return all wallets watched by the user"""
        wallets = WatchWallet.objects.prefetch_related(
            'wallet').filter(user=self.request.user)
        return wallets

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        total = 0.0
        augmented_wallets = []
        for wallet in context['wallets']:
            val = wallet.wallet.value()
            total += val
            augmented_wallets.append({"name": wallet.name, "wallet": wallet.wallet, "val": val,
                                     "val_1h": wallet.wallet.value_1h(), "val_24h": wallet.wallet.value_24h()})
        context['items'] = augmented_wallets
        context['total'] = total
        return context


@login_required
def wallet(request, wallet_address):
    wallet = get_object_or_404(Wallet, address=wallet_address.lower())
    tokens = wallet.get_tokens().select_related('token')
    token_values = {}
    for token in tokens:
        if token.token.liquidity or token.balance_calculated() == 0:
            continue
        last = token.get_last_value()
        if last is None:
            token_values[token] = None
            continue
        similar = last.get_similar()
        value = get_best_priced(similar)
        if value is None:
            token_values[token] = last
        else:
            token_values[token] = value
        

    return render(request, 'walletview/wallet.html', {'wallet': wallet, 'token_values': token_values})


def unzip(l):
    if len(l) == 0:
        return [[], []]
    return zip(*l)


@login_required
def wallet_token(request, wallet_address, token_id):
    wallet = get_object_or_404(Wallet, address=wallet_address.lower())
    token = get_object_or_404(Token, pk=token_id)
    wallet_token = wallet.wallettoken_set.filter(
        token=token).order_by('-fetched').first()

    # Balance
    (balance_ts, balance_data) = unzip([(balance.fetched.timestamp(), balance.balance_calculated(
    )) for balance in wallet.wallettoken_set.filter(token=token).order_by('fetched').iterator()])
    history_balance = mark_safe(json.dumps(
        [list(balance_ts), list(balance_data)]))

    # Value
    (value_ts, value_data) = unzip([(balance.fetched.timestamp(), balance.value_at_fetch(
    )) for balance in wallet.wallettoken_set.filter(token=token).order_by('fetched').iterator()])
    history_value = mark_safe(json.dumps([list(value_ts), list(value_data)]))

    # Price
    (price_ts, price_data) = unzip([(value.fetched.timestamp(), value.price)
                                   for value in token.tokenvalue_set.order_by('fetched').iterator()])
    history_price = mark_safe(json.dumps([list(price_ts), list(price_data)]))

    return render(request, 'walletview/wallettoken.html', {'wallet': wallet, 'token': token, 'wallet_token': wallet_token, 'history_balance': history_balance, 'history_value': history_value, 'history_price': history_price})


@login_required
def wallet_liquidity(request, wallet_address, liquidity_id):
    wallet = get_object_or_404(Wallet, address=wallet_address.lower())
    liquidity = get_object_or_404(LiquidityToken, pk=liquidity_id)
    wallet_liquidity = wallet.walletliquidity_set.filter(
        liquidity=liquidity).order_by('-fetched').first()

    # Balance
    (balance_ts, balance_data) = unzip([(balance.fetched.timestamp(), balance.balance)
                                        for balance in wallet.walletliquidity_set.filter(liquidity=liquidity).order_by('fetched').iterator()])
    history_balance = mark_safe(json.dumps(
        [list(balance_ts), list(balance_data)]))

    # Value
    (value_ts, value_data) = unzip([(balance.fetched.timestamp(), balance.value_at_fetch(
    )) for balance in wallet.walletliquidity_set.filter(liquidity=liquidity).order_by('fetched').iterator()])
    history_value = mark_safe(json.dumps([list(value_ts), list(value_data)]))

    # Price
    (price_ts, price_data) = unzip([(value.fetched.timestamp(), value.price)
                                   for value in liquidity.liquidityvalue_set.order_by('fetched').iterator()])
    history_price = mark_safe(json.dumps([list(price_ts), list(price_data)]))

    return render(request, 'walletview/walletliquidity.html', {'wallet': wallet, 'liquidity': liquidity, 'wallet_liquidity': wallet_liquidity, 'history_balance': history_balance, 'history_value': history_value, 'history_price': history_price})


@login_required
def add_wallet(request):
    if request.method == "POST":
        name = request.POST.get("name")
        wallet = request.POST.get("wallet").lower()
        if blockscout.fetch_wallet_balance(wallet) is not None:
            (wallet, created_wallet) = Wallet.objects.get_or_create(
                address=wallet, verified=True)
            (watch, _) = WatchWallet.objects.get_or_create(
                user=request.user, wallet=wallet, name=name)
            if created_wallet:
                wallet.update()
    return redirect("wallets")
