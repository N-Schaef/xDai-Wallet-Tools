
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

def fetch_all_liquidities(exchange_api,addresses):
    req_data = """
{{"query":
"{{users(where:{{id_in:[{addresses}]}}){{id,\\nliquidityPositions{{id,liquidityTokenBalance,pair{{id,totalSupply,reserveUSD,token0{{id,name,symbol}}token1{{id,name,symbol}}}}}}}}}}", "variables": null
}}
  """.format(addresses=','.join(map(lambda t: '\\"' + t + '\\"', addresses)))
    req_json = json.loads(req_data)
    liquidity_response = requests.post(exchange_api, json=req_json)
    ret = []
    if(liquidity_response.ok):
        data = liquidity_response.json()
        if "errors" in data:
            return ret
        users = data["data"]["users"]
        if users is None:
            return ret
        for user in users:
            liquidity_data = user["liquidityPositions"]
            for liquidity in liquidity_data:
                pair = liquidity["pair"]
                l = {
                'wallet':  user["id"],
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

def fetch_token_prices(exchange_api, tokens):
    sep = ','
    addresses = sep.join(map(lambda t: '\\"' + t + '\\"', tokens))
    req_data = """
{{"query":
"{{ tokens(where: {{id_in: [{tokens}]}}){{id,derivedETH}} }}", "variables": null
}}
  """.format(tokens=addresses)
    req_json = json.loads(req_data)

    pair_response = requests.post(exchange_api, json=req_json)
    if(pair_response.ok):
        data = json.loads(pair_response.content)
        if "errors" in data:
            print("Error in exchange backend: {}".format(data["errors"]))
            return []
        token_data = data["data"]["tokens"]
        if len(token_data) > 0:
            prices = {}
            for token in token_data:
                id = token["id"]
                if id not in prices:
                    prices[id] = float(token["derivedETH"])
            return prices
    else:
        print("Could not get data from {}".format(exchange_api))
    return []