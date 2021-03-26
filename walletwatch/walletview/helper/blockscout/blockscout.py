from django.conf import settings
import requests

def split_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def fetch_wallet_balances(addresses):
    res = {}
    for wallets_chunk in list(split_chunks(addresses, 100)):
        url = "{}{}{}".format(settings.BLOCKSCOUT_URL, settings.BLOCKSCOUT_MULTIPLE_BALANCE_ENDPOINT, ','.join(
            wallets_chunk))
        balance_response = requests.get(url)
        if(balance_response.ok):
            balance_data = balance_response.json()
            balances = balance_data["result"]

            for balance in balances:
                res[balance["account"].lower()] = balance["balance"]
    return res


def fetch_wallet_balance(address):
    url = "{}{}{}".format(
        settings.BLOCKSCOUT_URL, settings.BLOCKSCOUT_SINGLE_BALANCE_ENDPOINT, address)
    balance_response = requests.get(url)
    if(balance_response.ok):
        balance_data = balance_response.json()
        return balance_data["result"]
        


def fetch_tokens(address):
    url = "{}{}{}".format(
        settings.BLOCKSCOUT_URL, settings.BLOCKSCOUT_TOKENLIST_ENDPOINT, address)
    token_response = requests.get(url)
    ret = []
    if(token_response.ok):
        token_data = token_response.json()
        tokens = token_data["result"]
        for token in tokens:
          t = {
            'address': token['contractAddress'],
            'name': token['name'],
            'symbol': token['symbol'],
            'balance': token['balance'],
            'decimals': token['decimals']
          }
          ret.append(t)
    return ret
