
import json
import requests


def fetch_liquidities(exchange_api,address):
    req_data = """
{{"query":
"{{user(id: \\"{address}\\"){{\\nliquidityPositions{{id,liquidityTokenBalance,pair{{id,totalSupply,reserveUSD,token0{{id,name,symbol}}token1{{id,name,symbol}}}}}}}}}}", "variables": null
}}
  """.format(address=address.lower())
    req_json = json.loads(req_data)
    liquidity_response = requests.post(exchange_api, json=req_json)
    ret = []
    if(liquidity_response.ok):
        data = liquidity_response.json()
        if "errors" in data:
            return ret
        user = data["data"]["user"]
        if user is None:
            return ret
        liquidity_data = user["liquidityPositions"]
        for liquidity in liquidity_data:
            pair = liquidity["pair"]
            l = {
              'address': pair['id'],
              'token0': pair['token0'],
              'token1': pair['token1'],
              'balance': liquidity['liquidityTokenBalance'],
              'price': (float(pair["reserveUSD"]) / float(pair["totalSupply"])),
            }
            ret.append(l)
        return ret

def update_liquidities(exchange_api,tokens):
    req_data = """
{{"query":
"{{\\nliquidityPositions(where:{{id_in:[{addresses}]}}){{id,liquidityTokenBalance,pair{{id,totalSupply,reserveUSD,token0{{id,name,symbol}}token1{{id,name,symbol}}}}}}}}", "variables": null
}}
  """.format(addresses=','.join(map(lambda t: '\\"' + t + '\\"', tokens)))
    req_json = json.loads(req_data)
    liquidity_response = requests.post(exchange_api, json=req_json)
    ret = []
    if(liquidity_response.ok):
        data = liquidity_response.json()
        if "errors" in data:
            return ret
        liquidity_data = data["data"]["nliquidityPositions"]
        if liquidity_data is None:
            return ret
        for liquidity in liquidity_data:
            pair = liquidity["pair"]
            l = {
              'address': liquidity['pair'],
              'token0': pair['token0'],
              'token1': pair['token1'],
              'balance': liquidity['liquidityTokenBalance'],
              'price': (float(pair["reserveUSD"]) / float(pair["totalSupply"])),
            }
            ret.append(l)
        return ret
