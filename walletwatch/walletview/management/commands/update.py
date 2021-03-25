from walletview.models import Wallet, Token, TokenValue
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from walletview.helper import blockscout
import requests



def wallet_to_address(w):
    return w.address

class Command(BaseCommand):
    help = 'Fetches a new state'

    def handle(self, *args, **options):
        self.fetch_wallet_balance()
        self.fetch_token_balance()

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
            wallet.set_updated()

