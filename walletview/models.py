from typing import Dict
from django.db import models
from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from django.utils.timezone import make_aware
import requests
from .helper import blockscout, uniswap
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils.functional import cached_property

def format_address(address):
    return address.lower()

def query_before_ts_query(q, timestamp):
    if timestamp is not None:
        q.add(Q(fetched__lte=timestamp+timedelta(minutes=5)),Q.AND)
    return q

def query_before_1h_query(q):
    q.add(Q(fetched__lte=timezone.now()+timedelta(hours=-1)),Q.AND)
    return q

def query_before_24h_query(q):
    q.add(Q(fetched__lte=timezone.now()+timedelta(hours=-24)),Q.AND)
    return q

def query_within_5_min(q,timestamp):
    q.add(Q(fetched__lte=timestamp+timedelta(minutes=5)),Q.AND)
    q.add(Q(fetched__gte=timestamp+timedelta(minutes=-5)),Q.AND)
    return q

def query_from_exchange(q,exchange):
    if exchange is not None:
         q.add(Q(exchange=exchange),Q.AND) 
    return q

def get_best_priced(token_values):
    max_valued = (None,-1)
    for token in token_values:
        val = token.price
        if max_valued[0] == None or max_valued[1] < val:
            max_valued = (token,val)
    return max_valued[0]


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

    @property
    def fetched(self):
        return self.last_update
    
    def get_address(self):
        return format_address(self.address)

    def get_balance(self, filter=Q()):
        return self.walletbalance_set.filter(filter).order_by('-id').first()

    def get_tokens(self, filter=Q()):
        ids=self.wallettoken_set.filter(filter).values('token','wallet').annotate(Max('id'))
        id_list = [i['id__max'] for i in ids]
        return WalletToken.objects.filter(pk__in=id_list)

    def get_liquidities(self, filter=Q()):
        ids=self.walletliquidity_set.filter(filter).values('liquidity','wallet').annotate(Max('id'))
        id_list = [i['id__max'] for i in ids]
        return WalletLiquidity.objects.filter(pk__in=id_list)

    def value(self, filter=Q()):
        value = 0.0
        balance = self.get_balance(filter)
        if balance:
            value += balance.value()
        token_balances = dict()
        for token in self.get_tokens(filter).select_related('token'):
            token_balances[token.token_id]=token.balance_calculated()
        tv_q = Q(filter)
        tv_q.add(Q(token__in=token_balances.keys()),Q.AND)
        for token_value in TokenValue.get_values(tv_q):
            value += token_value.value(token_balances[token_value.token_id])
        
        liquidity_balances = dict()
        for liquidity in self.get_liquidities(filter):
            liquidity_balances[liquidity.liquidity_id]=liquidity.balance
        lv_q = Q(filter)
        lv_q.add(Q(liquidity__in=liquidity_balances.keys()),Q.AND)
        for liquidity_value in LiquidityValue.get_values(lv_q):
            value += liquidity_value.value(token_balances[liquidity_value.liquidity_id])
        return value
    
    def value_1h(self):
        return self.value(query_before_1h_query(Q()))
    def value_24h(self):
        return self.value(query_before_24h_query(Q()))

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


    def get_similar(self):
        q=Q(token=self.token)
        query_within_5_min(q,self.fetched)
        return TokenValue.objects.filter(q).exclude(id = self.id)

    def value(self, balance):
        return balance*self.price
    @staticmethod
    def get_values(q):
        ids=TokenValue.objects.filter(q).values('token').annotate(Max('id'))
        id_list = [i['id__max'] for i in ids]
        return TokenValue.objects.filter(pk__in=id_list)

    def __str__(self):
        return "{}: {} - {}".format(self.exchange.name,self.price, self.fetched)


class LiquidityValue(models.Model):
    liquidity = models.ForeignKey(LiquidityToken, on_delete=models.CASCADE)
    price = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    @staticmethod
    def get_values(q):
        ids=LiquidityValue.objects.filter(q).values('liquidity').annotate(Max('id'))
        id_list = [i['id__max'] for i in ids]
        return LiquidityValue.objects.filter(pk__in=id_list)

    def value(self, balance):
        return balance*self.price



class WalletLiquidity(models.Model):
    liquidity = models.ForeignKey(LiquidityToken, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)


    def get_last_value(self, filter=Q()):
        return self.liquidity.liquidityvalue_set.filter(filter).order_by('-fetched').first()
    
    def value_at_fetch(self):
        q=Q()
        query_before_ts_query(q,self.fetched)
        return self.value(q)

    def value(self, filter=Q()):
        s=self.get_last_value(filter)
        if s :
            return s.value(self.balance)
        return 0.0

    def value_1h(self):
        return self.value(query_before_1h_query(Q()))
    def value_24h(self):
        return self.value(query_before_24h_query(Q()))
    

class WalletToken(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    balance = models.CharField(max_length=250)
    decimals = models.IntegerField()
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def balance_calculated(self):
        return int(self.balance) / pow(10, self.decimals)


    def get_last_value(self,filter=Q()):
        return self.token.tokenvalue_set.filter(filter).order_by('-fetched').first()

    def value_at_fetch(self):
        q=Q()
        query_before_ts_query(q,self.fetched)
        return self.value(q)

    def value(self,filter=Q()):
        s=self.get_last_value(filter)
        if s :
            return s.value(self.balance_calculated())
        return 0.0

    def value_1h(self):
        return self.value(query_before_1h_query(Q()))
    def value_24h(self):
        return self.value(query_before_24h_query(Q()))
    


class WalletBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    xdai_balance = models.CharField(max_length=250)
    fetched = models.DateTimeField('fetched', auto_now_add=True, blank=True)

    def __str__(self):
        return "{} ({})".format(self.xdai(), self.fetched)

    def xdai(self):
        return int(self.xdai_balance) / pow(10, settings.BLOCKSCOUT_XDAI_BALANCE_DECIMALS)

    def value(self):
        return self.xdai()

