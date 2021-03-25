from walletview.models import Wallet
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import requests


def split_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def wallet_to_address(w):
    return w.address


class Command(BaseCommand):
    help = 'Fetches a new state'

    def handle(self, *args, **options):
        self.fetch_wallet_balance()

    def fetch_wallet_balance(self):
        wallets = Wallet.objects.filter(verified=True)
        for wallets_chunk in list(split_chunks(wallets, 100)):
            url = "{}{}{}".format(settings.BLOCKSCOUT_URL, settings.BLOCKSCOUT_MULTIPLE_BALANCE_ENDPOINT, ','.join(
                map(wallet_to_address, wallets_chunk)))
            balance_response = requests.get(url)
            if(balance_response.ok):
                balance_data = balance_response.json()
                balances = balance_data["result"]
                wallets_and_balance = zip(wallets_chunk, balances)
                for (wallet, balance) in wallets_and_balance:
                    if wallet.address.lower() != balance["account"].lower():
                        self.stdout.write(self.style.ERROR(
                            'Unexpected error during wallet/balance merge'))
                        return
                    wallet.walletbalance_set.create(
                        xdai_balance=balance["balance"])
            else:
                self.stdout.write(self.style.ERROR(
                    'Could not fetch wallet states from blockscout API'))
