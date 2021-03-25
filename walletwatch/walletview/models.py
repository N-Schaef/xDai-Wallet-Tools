from django.db import models
from django.conf import settings

 
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

class Wallet(models.Model):
    address = models.CharField(max_length=255,unique=True)
    verified = models.BooleanField(default=False)
    last_update = models.DateTimeField('last updated',auto_now_add=True, blank=True)

class WatchWallet:
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
    address = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=20)
    liquidity = models.BooleanField(default=False)

    def __str__(self):
        return "{}-{} ({})".format(self.symbol,self.name,self.address)


class LiquidityToken(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='liquidity_token')
    token0 = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='pair_token0')
    token1 = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='pair_token1')
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)

    def __str__(self):
        return "{}-{} ({})".format(self.token0.symbol,self.token1.symbol,self.exchange)

 


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
    fetched = models.DateTimeField('fetched',auto_now_add=True, blank=True)

class LiquidityValue(models.Model):
    liquidity = models.ForeignKey(LiquidityToken, on_delete=models.CASCADE)
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    value = models.FloatField(default=0.0)
    fetched = models.DateTimeField('fetched',auto_now_add=True, blank=True)

class WalletToken(models.Model):
    token = models.ForeignKey(Token, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    balance = models.CharField(max_length=250)
    decimals = models.IntegerField()
    fetched = models.DateTimeField('fetched',auto_now_add=True, blank=True)

    def balance_calculated(self):
        return int(self.balance) / pow(10, self.decimals)

class WalletBalance(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    xdai_balance = models.CharField(max_length=250)
    fetched = models.DateTimeField('fetched',auto_now_add=True, blank=True)

    def xdai(self):
        return int(self.xdai_balance) / pow(10, settings.BLOCKSCOUT_XDAI_BALANCE_DECIMALS)
