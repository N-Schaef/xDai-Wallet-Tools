from typing import Dict
from django.db import models
from django.conf import settings
from django.db.models import Max
from django.utils.timezone import make_aware
import requests
from .helper import blockscout, uniswap
from datetime import datetime, timedelta


def format_money(val):
    if val < 1.0:
        return "{:.3g} $".format(val)
    return "{:.2f} $".format(val)


def format_balance(val):
    if val < 1.0:
        return "{:.3g}".format(val)
    return "{:.2f}".format(val)

def format_address(address):
    return address.lower()


#     _____             __ _
#    / ____|           / _(_)
#   | |     ___  _ __ | |_ _  __ _
#   | |    / _ \| '_ \|  _| |/ _` |
#   | |___| (_) | | | | | | | (_| |
#    \_____\___/|_| |_|_| |_|\__, |
#                             __/ |
#                            |___/


class Exchange(models.Model):
    name = models.CharField(max_length=255)
    api = models.CharField(max_length=1000)
    factory_address = models.CharField(max_length=255)

    def __str__(self):
        return "{}".format(self.name)

    def update_tokens(self):
        Token.objects.all()


class Wallet(models.Model):
    address = models.CharField(max_length=255, unique=True)
    verified = models.BooleanField(default=False)
    last_update = models.DateTimeField(
        'last updated', auto_now_add=True, blank=True)

    def __str__(self):
        return "{} ({})".format(self.address,self.value())
    
    def get_address(self):
        return format_address(self.address)

    def get_balance(self):
        return self.walletbalance_set.order_by('-id').first()

    def get_tokens(self):
        ids=self.wallettoken_set.values('token','wallet').annotate(Max('id'))
        return [WalletToken.objects.get(pk=i['id__max']) for i in ids]

    def get_liquidities(self):
        ids=self.walletliquidity_set.values('liquidity','wallet').annotate(Max('id'))
        return [WalletLiquidity.objects.get(pk=i['id__max']) for i in ids]

    def value(self):
        value = 0.0
        balance = self.get_balance()
        if balance:
            value += balance.value()
        for token in self.get_tokens():
            value += token.value()
        for liquidity in self.get_liquidities():
            value += liquidity.value()
        return value

    def value_human(self):
        return format_money(self.value())

    def update(self):
        self.update_balance()
        self.update_tokens()
        self.update_liquidities()
        self.set_updated()

    def set_updated(self):
        self.last_update = make_aware(datetime.now())
        self.save()

    def update_balance(self):
        balance = blockscout.fetch_wallet_balance(self.address)
        self.walletbalance_set.create(xdai_balance=balance)

    def update_liquidities(self):
        for exchange in Exchange.objects.all():
            liquidities = uniswap.fetch_liquidities(exchange.api, self.address)
            for l in liquidities:
                liquidity = LiquidityToken.ensure(l, exchange)
                if liquidity:
                    liquidity.liquidityvalue_set.create(price=l['price'])
                    liquidity.walletliquidity_set.create(
                        wallet=self, balance=l['balance'])

    def update_tokens(self):
        tokens = blockscout.fetch_tokens(self.address)
        old_tokens = self.get_tokens()
        updated = []
        for token in tokens:
            (token_obj, _) = Token.objects.get_or_create(
                address=token['address'], name=token['name'], symbol=token['symbol'])
            self.wallettoken_set.create(
                token=token_obj, balance=token['balance'], decimals=int(token['decimals']))
            updated.append(format_address(token['address']))
        for token in old_tokens:
            if token.token.get_address() not in updated:
                self.wallettoken_set.create(token=token.token, balance=0, decimals=token.decimals)


class WatchWallet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)


#    _____                      _ _
#   |  __ \                    (_) |
#   | |__) |___ _ __   ___  ___ _| |_ ___  _ __ _   _
#   |  _  // _ \ '_ \ / _ \/ __| | __/ _ \| '__| | | |
#   | | \ \  __/ |_) | (_) \__ \ | || (_) | |  | |_| |
#   |_|  \_\___| .__/ \___/|___/_|\__\___/|_|   \__, |
#              | |                               __/ |
#              |_|                              |___/


class Token(models.Model):
    address = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=255)
    liquidity = models.BooleanField(default=False)

    def __str__(self):
        return "{} {} ({})".format(self.symbol, self.name, self.address)
    
    def get_address(self):
        return format_address(self.address)


class LiquidityToken(models.Model):
    token = models.OneToOneField(
        Token,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    token0 = models.ForeignKey(
        Token, on_delete=models.CASCADE, related_name='pair_token0')
    token1 = models.ForeignKey(
        Token, on_delete=models.CASCADE, related_name='pair_token1')
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)

    def __str__(self):
        return "{}-{} ({})".format(self.token0.symbol, self.token1.symbol, self.exchange)

    def pair(self):
        return "{}-{}".format(self.token0.symbol, self.token1.symbol)

    @staticmethod
    def ensure(liquidity, exchange):
        try:
            token = Token.objects.get(address=liquidity['address'])
        except Token.DoesNotExist:
            return None

        token.liquidity = True
        token.save()
        t0 = liquidity['token0']
        t1 = liquidity['token1']
        (token0, _) = Token.objects.get_or_create(
            address=t0['id'], name=t0['name'], symbol=t0['symbol'])
        (token1, _) = Token.objects.get_or_create(
            address=t1['id'], name=t1['name'], symbol=t1['symbol'])
        (l, _) = LiquidityToken.objects.get_or_create(
            token=token, token0=token0, token1=token1, exchange=exchange)
        return l


#     _____ _        _
#    / ____| |      | |
#   | (___ | |_ __ _| |_ _   _ ___
#    \___ \| __/ _` | __| | | / __|
#    ____) | || (_| | |_| |_| \__ \
#   |_____/ \__\__,_|\__|\__,_|___/



class TokenValue(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    price = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def value(self, balance):
        return balance*self.price
    
    def price_human(self):
        return format_money(self.price)

    def __str__(self):
        return "{}: {} - {}".format(self.exchange.name,self.price_human(), self.fetched)


class LiquidityValue(models.Model):
    liquidity = models.ForeignKey(LiquidityToken, on_delete=models.CASCADE)
    price = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def value(self, balance):
        return balance*self.price

    def price_human(self):
        return format_money(self.price)


class WalletLiquidity(models.Model):
    liquidity = models.ForeignKey(LiquidityToken, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def get_last_value(self):
        return self.liquidity.liquidityvalue_set.order_by('-fetched').first()

    def value(self):
        s=self.get_last_value()
        if s :
            return s.value(self.balance)
        return 0.0
    
    def balance_human(self):
        return format_balance(self.balance)

    def value_human(self):
        return format_money(self.value())

class WalletToken(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    balance = models.CharField(max_length=250)
    decimals = models.IntegerField()
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def balance_calculated(self):
        return int(self.balance) / pow(10, self.decimals)

    def balance_human(self):
        return format_balance(self.balance_calculated())

    def get_last_value(self):
        return self.token.tokenvalue_set.order_by('-fetched').first()

    def get_last_value_at_fetch(self):
        return self.token.tokenvalue_set.order_by('-fetched').filter(fetched__lte=self.fetched+timedelta(minutes=5)).first()
    
    def get_last_values(self):
        num_exchanges = Exchange.objects.count()
        values = self.token.tokenvalue_set.order_by('-fetched')[:num_exchanges]
        val_dict =  {}
        for value in values:
            exchange_name = value.exchange.name
            if value.exchange.name not in val_dict:
                val_dict[exchange_name] = value
        return val_dict

    def value(self):
        s=self.get_last_value()
        if s :
            return s.value(self.balance_calculated())
        return 0.0
    
    def value_at_fetch(self):
        s=self.get_last_value_at_fetch()
        if s :
            return s.value(self.balance_calculated())
        return 0.0

    def value_human(self):
        return format_money(self.value())


class WalletBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    xdai_balance = models.CharField(max_length=250)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def __str__(self):
        return "{} ({})".format(format_balance(self.xdai()), self.fetched)

    def xdai(self):
        return int(self.xdai_balance) / pow(10, settings.BLOCKSCOUT_XDAI_BALANCE_DECIMALS)

    def xdai_human(self):
        return format_balance(self.xdai())

    def value(self):
        return self.xdai()

    def value_human(self):
        return format_money(self.value())
