#!/usr/bin/env python3

import click
import json  # standard JSON parser
import requests  # HTTP library
import sqlite3
from prettytable import PrettyTable
from datetime import datetime

blockscout_url = "https://blockscout.com/xdai/mainnet/api"
db_file = "wallettools.sqlite"

#    _____  ____
#   |  __ \|  _ \
#   | |  | | |_) |
#   | |  | |  _ <
#   | |__| | |_) |
#   |_____/|____/


def init_db(file):
    con = sqlite3.connect(file)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS state
        (id INTEGER PRIMARY KEY, wallet_address VARCHAR(255), timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS token
        (id INTEGER PRIMARY KEY, address VARCHAR(255) UNIQUE, name VARCHAR(255), symbol VARCHAR(20))''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS wallet
        (state_id INTEGER REFERENCES state(id), token_id INTEGER REFERENCES token(id), balance VARCHAR(255), decimals INTEGER, price REAL)''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS liqudity
        (state_id INTEGER REFERENCES state(id), token0_id INTEGER REFERENCES token(id), token1_id INTEGER REFERENCES token(id), balance REAL, price REAL)''')

    con.commit()
    con.close()


def insert_token(file, address, name, symbol):
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.execute('INSERT INTO token (address,name,symbol) values(?,?,?) ON CONFLICT(address) DO UPDATE SET name=excluded.name, symbol=excluded.symbol;',
                (address, name, symbol,))
    con.commit()
    rowId = None
    for row in cur.execute('SELECT id FROM token where address = ?',
                           (address, )):
        rowId = row[0]
    con.close()
    return rowId


def fetch_db(file, wallet, exchanges):
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.execute('INSERT INTO state(wallet_address) VALUES (?)', (wallet,))
    rowid = cur.lastrowid
    con.commit()
    con.close()
    insert_tokens(file, rowid, wallet, exchanges[0])
    for exchange in exchanges:
        insert_liquidity(file, rowid, wallet, exchange)


def insert_tokens(file, state, wallet, exchange):
    rows = fetch_tokens(wallet, state, exchange)
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.executemany(
        'INSERT INTO wallet(state_id,token_id, balance, decimals, price) VALUES (?,?,?,?,?)', rows)
    con.commit()
    con.close()


def insert_liquidity(file, state, wallet, exchange):
    rows = fetch_liquidities(wallet, state, exchange)
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.executemany(
        'INSERT INTO liqudity(state_id,token0_id,token1_id, balance, price) VALUES (?,?,?,?,?)', rows)
    con.commit()
    con.close()


def get_last_state_id(file, wallet):
    con = sqlite3.connect(file)
    cur = con.cursor()
    for row in cur.execute('SELECT id, timestamp FROM state WHERE wallet_address = ? ORDER BY id DESC LIMIT 1;', (wallet,)):
        return (row[0],row[1])
    con.close()
    return None


def print_token_state(file, state):
    con = sqlite3.connect(file)
    cur = con.cursor()
    table = PrettyTable()
    table.field_names = ["Name", "Symbol", "Balance", "Price", "Value"]
    total_val = 0.0
    for row in cur.execute("SELECT token.name as name, token.symbol as symbol, wallet.balance, wallet.decimals, wallet.price FROM wallet INNER JOIN token ON wallet.token_id = token.id WHERE wallet.state_id = ?;", (state,)):
        balance = int(row[2])/pow(10, row[3])
        total = balance*row[4]
        total_val += total
        table.add_row([row[0], row[1], balance,
                       row[4], "{:.2f}$".format(total)])
    print("==== Token Balance ====")
    print(table)
    total = "{:.2f}$".format(total_val)
    print_table_summary(table,"Total",total)
    return total_val


def print_liquidity_state(file, state):
    con = sqlite3.connect(file)
    cur = con.cursor()
    table = PrettyTable()
    table.field_names = ["Pair", "Balance", "Value"]
    total_val = 0.0
    for row in cur.execute("SELECT t0.symbol,  t1.symbol, l.balance, l.price FROM (liqudity l INNER JOIN token t0 ON l.token0_id = t0.id) INNER JOIN token t1 ON l.token1_id = t1.id  WHERE l.state_id = ?;", (state,)):
        total_val += row[3]
        table.add_row(["{}-{}".format(row[0], row[1]),
                       row[2], "{:.2f}$".format(row[3])])
    print("==== Liquidity Pool Balance ====")
    print(table)
    total = "{:.2f}$".format(total_val)
    print_table_summary(table,"Total",total)
    return total_val


def print_wallet_state(file, state, time, wallet):
    print("State {} from {} for wallet address {}".format(state,time,wallet))
    total = print_token_state(file, state)
    total += print_liquidity_state(file, state)
    print("=== Total wallet value: {:.2f}$ ===".format(total))

#  __  __ _
# |  \/  (_)
# | \  / |_ ___  ___
# | |\/| | / __|/ __|
# | |  | | \__ \ (__
# |_|  |_|_|___/\___|


def format_wallet_address(wallet):
    return wallet.lower()

def print_table_summary(table, summary_title, summary_value):
    padding_bw = (3 * (len(table.field_names)-1))
    tb_width = sum(table._widths)
    print('| ' + summary_title + (' ' * (tb_width - len(summary_title + summary_value)) +
                            ' ' * padding_bw) + summary_value + ' |')
    print('+-' + '-' * tb_width + '-' * padding_bw + '-+')

#  _    _       _                           __  __ _
# | |  | |     (_)                         |  \/  (_)
# | |  | |_ __  _ _____      ____ _ _ __   | \  / |_ ___  ___
# | |  | | '_ \| / __\ \ /\ / / _` | '_ \  | |\/| | / __|/ __|
# | |__| | | | | \__ \\ V  V / (_| | |_) | | |  | | \__ \ (__
#  \____/|_| |_|_|___/ \_/\_/ \__,_| .__/  |_|  |_|_|___/\___|
#                                  | |
#                                  |_|
def fetch_liquidities(wallet, state, exchange):
    req_data = """
{{"query":
"{{user(id: \\"{wallet}\\"){{\\nliquidityPositions{{id,liquidityTokenBalance,pair{{totalSupply,reserveUSD,token0{{id,name,symbol}}token1{{id,name,symbol}}}}}}}}}}", "variables": null
}}
  """.format(wallet=format_wallet_address(wallet))
    req_json = json.loads(req_data)
    liquidity_response = requests.post(exchange, json=req_json)
    if(liquidity_response.ok):
        data = json.loads(liquidity_response.content)
        user = data["data"]["user"]
        if user is None:
            return None
        liquidity_data = user["liquidityPositions"]
        liquidity_rows = []
        for liquidity in liquidity_data:
            pair = liquidity["pair"]
            token0 = pair["token0"]
            token0_id = insert_token(
                db_file, token0["id"], token0["name"], token0["symbol"])
            token1 = pair["token1"]
            token1_id = insert_token(
                db_file, token1["id"], token1["name"], token1["symbol"])
            pool_amount = (float(
                pair["reserveUSD"])/float(pair["totalSupply"]))*float(liquidity["liquidityTokenBalance"])
            row = (state, token0_id, token1_id, float(
                liquidity["liquidityTokenBalance"]), pool_amount,)
            liquidity_rows.append(row)
        return liquidity_rows
    else:
        print("Could not connect to {}".format(exchange))


#  _______    _
# |__   __|  | |
#    | | ___ | | _____ _ __  ___
#    | |/ _ \| |/ / _ \ '_ \/ __|
#    | | (_) |   <  __/ | | \__ \
#    |_|\___/|_|\_\___|_| |_|___/


def fetch_token_price(exchange_url, token_address):
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
            return float(token_data[0]["priceUSD"])
    else:
        print("Could not get data from {}".format(exchange_url))
    return None


def fetch_tokens(wallet, state_id, exchange):
    endpoint = "?module=account&action=tokenlist&address={}".format(
        format_wallet_address(wallet))
    url = "{}{}".format(blockscout_url, endpoint)
    token_response = requests.get(url)
    if(token_response.ok):
        data = json.loads(token_response.content)
        tokens = data["result"]
        wallet_rows = []
        for token in tokens:
            if int(token["balance"]) == 0:
                continue
            token_id = insert_token(
                db_file, token["contractAddress"], token["name"], token["symbol"])
            token_value = fetch_token_price(exchange, token["contractAddress"])
            if token_value is None:
                token_value = 0.0
            if token_value is not None:
                row = (state_id, token_id, token["balance"], int(
                    token["decimals"]), token_value,)
                wallet_rows.append(row)
        return wallet_rows
    else:
        print("Could not connect to {}".format(url))
        return None


def tokens(args):
    init_db(db_file)
    fetch_db(db_file, args.wallet, args.exchange)


#
#    _____ _      _____
#   / ____| |    |_   _|
#  | |    | |      | |
#  | |    | |      | |
#  | |____| |____ _| |_
#   \_____|______|_____|
#

default_db = "wallettools.sqlite"


@click.group()
def cli():
    pass


@cli.command()
@click.option('--wallet', help='Your xDai wallet address', required=True)
@click.option('--db', help='The SQLite DB file', default=default_db)
@click.option('--exchange', help='Uniswap V2 compatible exchange APIs to query', multiple=True, default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
def update(wallet, db, exchange):
    """Fetches the current state of your wallet."""
    init_db(db)
    fetch_db(db, format_wallet_address(wallet), exchange)


@cli.command()
@click.option('--wallet', help='Your xDai wallet address', required=True)
@click.option('--db', help='The SQLite DB file', default=default_db)
@click.option('--exchange', help='Uniswap V2 compatible exchange APIs to query', multiple=True, default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
@click.option('--fetch/--no-fetch', default=True, help='Fetch new data before displaying')
def show(wallet, db, exchange, fetch):
    """Shows the last state of your wallet"""
    init_db(db)
    if fetch:
        fetch_db(db, format_wallet_address(wallet), exchange)
    state = get_last_state_id(db, format_wallet_address(wallet))
    if state is None:
        print("Could not find any state for wallet address {}".format(wallet))
        return
    print_wallet_state(db, state[0], "{}".format(state[1]),wallet)


if __name__ == '__main__':
    cli()
