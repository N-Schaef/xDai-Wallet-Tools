#!/usr/bin/env python3

import argparse
import json  # standard JSON parser
import requests  # HTTP library
blockscout_url = "https://blockscout.com/xdai/mainnet/api"
xdai_address = "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d"
usdc_address = "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83"

#  __  __ _
# |  \/  (_)
# | \  / |_ ___  ___
# | |\/| | / __|/ __|
# | |  | | \__ \ (__
# |_|  |_|_|___/\___|


def format_wallet_address(wallet):
    return wallet.lower()


#  _    _       _                           __  __ _
# | |  | |     (_)                         |  \/  (_)
# | |  | |_ __  _ _____      ____ _ _ __   | \  / |_ ___  ___
# | |  | | '_ \| / __\ \ /\ / / _` | '_ \  | |\/| | / __|/ __|
# | |__| | | | | \__ \\ V  V / (_| | |_) | | |  | | \__ \ (__
#  \____/|_| |_|_|___/ \_/\_/ \__,_| .__/  |_|  |_|_|___/\___|
#                                  | |
#                                  |_|
def get_liquidities(args):
    req_data = """                   
{{"query":
"{{user(id: \\"{wallet}\\"){{\\nliquidityPositions{{id,liquidityTokenBalance,pair{{totalSupply,reserveUSD,token0{{name,symbol}}token1{{name,symbol}}}}}}}}}}", "variables": null
}}
  """.format(wallet=format_wallet_address(args.wallet))
    req_json = json.loads(req_data)
    overall_liquidity = 0.0
    print(args.exchange)
    for exchange in args.exchange:
        exchange_liquidity = 0.0
        liquidity_response = requests.post(exchange, json=req_json)
        print("--- Liquidity pools in exchange {} ---".format(exchange))
        if(liquidity_response.ok):
            data = json.loads(liquidity_response.content)
            user = data["data"]["user"]
            if user is None:
                continue
            liquidity_data = user["liquidityPositions"]
            for liquidity in liquidity_data:
                pair = liquidity["pair"]
                pool_amount = (float(
                    pair["reserveUSD"])/float(pair["totalSupply"]))*float(liquidity["liquidityTokenBalance"])
                print(
                    "{}-{}: {:.2f}$".format(pair["token0"]["symbol"], pair["token1"]["symbol"], pool_amount))
                exchange_liquidity += pool_amount
            print("---")
            print("Exchange Sum: {:.2f} $".format(exchange_liquidity))
            overall_liquidity += exchange_liquidity

        else:
            print("Could not connect to {}".format(exchange))

        print("-------")
        print("Overall Sum: {:.2f} $".format(overall_liquidity))
        return overall_liquidity


#  _______    _
# |__   __|  | |
#    | | ___ | | _____ _ __  ___
#    | |/ _ \| |/ / _ \ '_ \/ __|
#    | | (_) |   <  __/ | | \__ \
#    |_|\___/|_|\_\___|_| |_|___/

def get_token_value(exchange_url, token_address, amount):
    req_data = """
                    
{{"query":
"{{ tokenDayDatas(where: {{token:\\"{token}\\"}},orderBy: date, orderDirection: desc,first:1) {{id \\n priceUSD\\n date }}}}", "variables": null
}}
  """.format(token=token_address)
    req_json = json.loads(req_data)

    pair_response = requests.post(exchange_url, json=req_json)
    if(pair_response.ok):
        data = json.loads(pair_response.content)
        token_data = data["data"]["tokenDayDatas"]
        if len(token_data) > 0:
            return amount * float(token_data[0]["priceUSD"])
    else:
        print("Could not get data from {}".format(exchange_url))
        print(pair_response)
    return None


def tokens(args):
    print("--- Tokens in wallet {} ---".format(args.wallet))
    endpoint = "?module=account&action=tokenlist&address={}".format(
        format_wallet_address(args.wallet))
    url = "{}{}".format(blockscout_url, endpoint)
    token_response = requests.get(url)
    if(token_response.ok):
        data = json.loads(token_response.content)
        tokens = data["result"]
        overall_value = 0.0
        for token in tokens:
            bal = int(token["balance"])
            if bal == 0.0:
                continue
            balance = bal/pow(10.0, int(token["decimals"]))
            token_value = get_token_value(
                args.exchange, token["contractAddress"], balance)
            if token_value is None:
                token_value = 0.0
            print("{}({}): {} = {:.2f}$".format(
                token["name"], token["symbol"], balance,  token_value))
            if token_value is not None:
                overall_value += token_value
        print("-------")
        print("Sum: {:.2f} $".format(overall_value))
        return overall_value
    else:
        print("Could not connect to {}".format(url))
        return 0.0


def wallet_balance(args):
    overall_balance = 0.0
    overall_balance += get_liquidities(args)
    args.exchange = args.exchange[0]
    overall_balance += tokens(args)
    print("===Total Balance===")
    print("{:.2f} $".format(overall_balance))


#
#    _____ _      _____
#   / ____| |    |_   _|
#  | |    | |      | |
#  | |    | |      | |
#  | |____| |____ _| |_
#   \_____|______|_____|
#
parser = argparse.ArgumentParser(
    description='A collection of tools to handle xDai chain wallets.')
walletcommands = parser.add_subparsers(title='Wallet',
                                       description='Commands using your wallet')
tokens_parser = walletcommands.add_parser('tokens')
tokens_parser.add_argument('--wallet', required=True,
                           help='Your wallet address')
tokens_parser.add_argument('--exchange',
                           help='Uniswap v2 compatible exchange URL', default="https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2")
tokens_parser.set_defaults(func=tokens)

pools_parser = walletcommands.add_parser('pools')
pools_parser.add_argument('--wallet', required=True,
                          help='Your wallet address')
pools_parser.add_argument('--exchange', action='append',
                          help='Uniswap v2 compatible exchange URL', default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
pools_parser.set_defaults(func=get_liquidities)

balance_parser = walletcommands.add_parser('balance')
balance_parser.add_argument('--wallet', required=True,
                            help='Your wallet address')
balance_parser.add_argument('--exchange', action='append',
                            help='Uniswap v2 compatible exchange URL', default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
balance_parser.set_defaults(func=wallet_balance)

args = parser.parse_args()
args.func(args)
