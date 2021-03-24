from django.db import models
from django.conf import settings

# Create your models here.


class Wallet(models.Model):
    address = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    last_update = models.DateTimeField('last updated')

class WatchWallet:
  user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
  wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)

# One Token
class Token(models.Model):
    address = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=20)
    liquidity = models.BooleanField(default=False)

    def __str__(self):
        return "{}-{} ({})".format(self.symbol,self.name,self.address)

class Exchange(models.Model):
    name = models.CharField(max_length=255)
    api = models.CharField(max_length=1000)
    factory_address = models.CharField(max_length=255)

    def __str__(self):
        return "{}".format(self.name)


class LiquidityToken(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='liquidity_token')
    token0 = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='pair_token0')
    token1 = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='pair_token1')
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)

    def __str__(self):
        return "{}-{} ({})".format(self.token0.symbol,self.token1.symbol,self.exchange)