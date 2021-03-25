from django.contrib import admin


from .models import Token, Exchange, LiquidityToken, Wallet, WalletBalance, WatchWallet 

# Register your models here.
admin.site.register(Token)
admin.site.register(Exchange)
admin.site.register(LiquidityToken)
admin.site.register(Wallet)
admin.site.register(WalletBalance)