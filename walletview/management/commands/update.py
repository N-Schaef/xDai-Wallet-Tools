from walletview.models import Wallet, Token, LiquidityToken, Exchange
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from walletview.helper import blockscout, uniswap
import requests



def wallet_to_address(w):
    return w.get_address()

class Command(BaseCommand):
    help = 'Fetches a new state'

    def handle(self, *args, **options):
        self.fetch_wallet_balance()
        self.fetch_token_balance()
        self.fetch_token_price()
        self.fetch_liquidities()
        self.update_wallet_status()


    def fetch_wallet_balance(self):
        wallets = Wallet.objects.filter(verified=True)
        self.stdout.write("Fetching coin balances for {} wallets".format(wallets.count()))
        balances = blockscout.fetch_wallet_balances(list(map(wallet_to_address,wallets))) 
        for wallet in wallets:
            address = wallet.get_address()
            if address not in balances:
                self.stdout.write(self.style.ERROR("Could not fetch balance for wallet {}".format(address)))
                continue
            wallet.walletbalance_set.create(xdai_balance=balances[address])

    
    def fetch_token_balance(self):
        wallets = Wallet.objects.filter(verified=True)
        self.stdout.write("Fetching token balances for {} wallets".format(wallets.count()))
        for wallet in wallets:
            wallet.update_tokens()

    def fetch_token_price(self):
        exchanges = Exchange.objects.all()
        tokens = Token.objects.all()
        self.stdout.write("Fetching token prices for {} tokens on {} exchanges".format(tokens.count(),exchanges.count()))
        addresses = list(map(wallet_to_address,tokens))
        for exchange in exchanges:
            prices = uniswap.fetch_token_prices(exchange.api,addresses)
            self.stdout.write("Fetched {} prices from {}".format(len(prices),exchange.name))
            for token in tokens:
                if token.address in prices:
                    token.tokenvalue_set.create(exchange=exchange,price=prices[token.address])

    def fetch_liquidities(self):
        exchanges = Exchange.objects.all()
        wallets = Wallet.objects.all()
        addresses = list(map(wallet_to_address,wallets))
        self.stdout.write("Fetching liquidities {} wallets on {} exchanges".format(wallets.count(),exchanges.count()))
        updated = dict()
        for exchange in exchanges:
            liquidities = uniswap.fetch_all_liquidities(exchange.api,addresses)
            self.stdout.write("Fetched {} liquidities from {}".format(len(liquidities),exchange.name))
            for l in liquidities:
                liquidity = LiquidityToken.ensure(l, exchange)
                if liquidity:
                    liquidity.liquidityvalue_set.create(price=l['price'])
                    liquidity.walletliquidity_set.create(
                        wallet=Wallet.objects.get(address=l['wallet']), balance=l['balance'])
                    if l['wallet'] not in updated:
                        updated[l['wallet']] = [liquidity.token.get_address()]
                    else:
                        updated[l['wallet']].append(liquidity.token.get_address())
        for wallet in wallets:
            update = updated.get(wallet.get_address(),[])
            for old_liquidity in wallet.get_liquidities():
                if old_liquidity.liquidity.token.get_address() not in update:
                    wallet.walletliquidity_set.create(liquidity=old_liquidity.liquidity, balance=0) 

                    


    def update_wallet(self):
        wallets = Wallet.objects.filter(verified=True)
        self.stdout.write("Updating {} wallets".format(wallets.count()))
        for wallet in wallets:
            wallet.update()
    
    def update_wallet_status(self):
        wallets = Wallet.objects.filter(verified=True)
        self.stdout.write("Updating status of {} wallets".format(wallets.count()))
        for wallet in wallets:
            wallet.set_updated()

