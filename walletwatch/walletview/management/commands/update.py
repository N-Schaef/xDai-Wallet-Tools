from walletview.models import Wallet, Token, TokenValue, Exchange
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from walletview.helper import blockscout, uniswap
import requests



def wallet_to_address(w):
    return w.address

class Command(BaseCommand):
    help = 'Fetches a new state'

    def handle(self, *args, **options):
        #self.fetch_wallet_balance()
        self.update_wallet()
        self.fetch_token_price()

    def fetch_wallet_balance(self):
        wallets = Wallet.objects.filter(verified=True)

        balances = blockscout.fetch_wallet_balances(list(map(wallet_to_address,wallets)))

        for (wallet, balance) in zip(wallets,balances):
            if wallet.address.lower() != balance[0]:
                self.stdout.write(self.style.ERROR(
                    'Error merging wallets with fetched balances'))
                return
            wallet.walletbalance_set.create(
                        xdai_balance=balance[1])

    
    def fetch_token_balance(self):
        wallets = Wallet.objects.filter(verified=True)
        for wallet in wallets:
            wallet.update_tokens()

    def fetch_token_price(self):
        exchanges = Exchange.objects.all()
        tokens = Token.objects.all()
        addresses = list(map(wallet_to_address,tokens))
        for exchange in exchanges:
            prices = uniswap.fetch_token_prices(exchange.api,addresses)
            for token in tokens:
                if token.address in prices:
                    token.tokenvalue_set.create(exchange=exchange,price=prices[token.address])


    def update_wallet(self):
        wallets = Wallet.objects.filter(verified=True)
        for wallet in wallets:
            wallet.update()

