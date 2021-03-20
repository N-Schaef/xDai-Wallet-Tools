#!/usr/bin/env python3

import click
import json  # standard JSON parser
import requests  # HTTP library
import sqlite3
from prettytable import PrettyTable, from_db_cursor
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
    cur.execute('''PRAGMA foreign_keys = ON;''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS state
        (id INTEGER PRIMARY KEY, wallet_address VARCHAR(255), timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS token
        (id INTEGER PRIMARY KEY, address VARCHAR(255) UNIQUE, name VARCHAR(255), symbol VARCHAR(20));''')
    cur.execute('''
        INSERT OR IGNORE INTO token (id, address, name, symbol) VALUES(1,'0x0000000000000000000000000000000000000000', 'xDAI', 'xDAI')
        ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS wallet
        (state_id INTEGER, token_id INTEGER, balance VARCHAR(255), decimals INTEGER, price REAL,
        FOREIGN KEY(state_id) REFERENCES state(id) ON DELETE CASCADE,
        FOREIGN KEY(token_id) REFERENCES token(id) ON DELETE CASCADE
        )
        ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS liqudity
        (state_id INTEGER REFERENCES state(id), token0_id INTEGER REFERENCES token(id), token1_id INTEGER REFERENCES token(id), balance REAL, price REAL,
        FOREIGN KEY(state_id) REFERENCES state(id) ON DELETE CASCADE,
        FOREIGN KEY(token0_id) REFERENCES token(id) ON DELETE CASCADE,
        FOREIGN KEY(token1_id) REFERENCES token(id) ON DELETE CASCADE
        )
        ''')

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
    coin = fetch_coin(wallet, state)
    rows = fetch_tokens(wallet, state, exchange)
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.execute(
        'INSERT INTO wallet(state_id,token_id, balance, decimals, price) VALUES (?,1,?,18,1.0)', (state, coin))
    cur.executemany(
        'INSERT INTO wallet(state_id,token_id, balance, decimals, price) VALUES (?,?,?,?,?)', rows)
    con.commit()
    con.close()


def insert_liquidity(file, state, wallet, exchange):
    rows = fetch_liquidities(wallet, state, exchange)
    if rows is None:
        return
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.executemany(
        'INSERT INTO liqudity(state_id,token0_id,token1_id, balance, price) VALUES (?,?,?,?,?)', rows)
    con.commit()
    con.close()


def get_last_state_id(file, wallet):
    con = sqlite3.connect(file)
    cur = con.cursor()
    for row in cur.execute('SELECT id FROM state WHERE wallet_address = ? ORDER BY id DESC LIMIT 1;', (wallet,)):
        return row[0]
    con.close()
    return None

def get_previous_state_id(file, state):
    con = sqlite3.connect(file)
    cur = con.cursor()
    for row in cur.execute('SELECT s1.id FROM state s1 INNER JOIN state s2 ON s1.wallet_address = s2.wallet_address WHERE s2.id = ?  AND s1.id < s2.id ORDER BY s1.id DESC LIMIT 1;', (state,)):
        return row[0]
    con.close()
    return None

def get_state_id(file, state):
    con = sqlite3.connect(file)
    cur = con.cursor()
    for row in cur.execute('SELECT id, wallet_address, timestamp FROM state WHERE id = ? ORDER BY id DESC LIMIT 1;', (state,)):
        return (row[0], row[1], row[2])
    con.close()
    return None



def print_token_state(file, state, compare=None):
    con = sqlite3.connect(file)
    cur = con.cursor()
    table = PrettyTable()
    table.field_names = ["Name", "Symbol", "Balance", "Price", "Value"]
    total_val = 0.0
    old_total = 0.0
    contents = {}

    for row in cur.execute("SELECT token.name as name, token.symbol as symbol, wallet.balance, wallet.decimals, wallet.price, token.id FROM wallet INNER JOIN token ON wallet.token_id = token.id WHERE wallet.state_id = ?;", (state,)):
        balance = int(row[2])/pow(10, row[3])
        total = balance*row[4]
        total_val += total
        contents[row[5]] = [row[0], row[1], balance,
                            row[4], total]
    if compare is not None:

        for row in cur.execute("SELECT token.name as name, token.symbol as symbol, wallet.balance, wallet.decimals, wallet.price, token.id FROM wallet INNER JOIN token ON wallet.token_id = token.id WHERE wallet.state_id = ?;", (compare,)):
            balance = int(row[2])/pow(10, row[3])
            total = balance*row[4]
            old_total += total
            if row[5] in contents:
                old = contents[row[5]]
                contents[row[5]] = [old[0], old[1], format_balance(old[2], get_perc_diff(
                    old[2], balance)), format_money(old[3], get_perc_diff(old[3], row[4])), format_money(old[4], get_perc_diff(old[4], total))]
            else:
                contents[row[5]] = [row[0], row[1], balance,
                                    row[4], "{:.2f}".format(total)]
    for row in contents.items():
        r = row[1]
        if not isinstance(r[2],str):
            r[2] = format_balance(r[2])
        if not isinstance(r[3],str):
            r[3] = format_money(r[3])
        if not isinstance(r[4],str):
            r[4] = format_money(r[4])
        table.add_row(row[1])
    table.align = "l"
    print("==== Token Balance ====")
    print(table)
    total = format_money(total_val, get_perc_diff(old_total, total_val))
    print_table_summary(table, "Total", total)
    return (total_val, old_total)


def print_liquidity_state(file, state, compare=None):
    con = sqlite3.connect(file)
    cur = con.cursor()
    table = PrettyTable()
    table.field_names = ["Pair", "Balance", "Value"]
    total_val = 0.0
    old_total = 0.0
    contents = {}
    for row in cur.execute("SELECT t0.symbol,  t1.symbol, l.balance, l.price, l.token0_id, l.token1_id FROM (liqudity l INNER JOIN token t0 ON l.token0_id = t0.id) INNER JOIN token t1 ON l.token1_id = t1.id  WHERE l.state_id = ?;", (state,)):
        total_val += row[3]
        contents[(row[4], row[5])] = [
            "{}-{}".format(row[0], row[1]), row[2], row[3]]
    if compare is not None:
        for row in cur.execute("SELECT t0.symbol,  t1.symbol, l.balance, l.price, l.token0_id, l.token1_id FROM (liqudity l INNER JOIN token t0 ON l.token0_id = t0.id) INNER JOIN token t1 ON l.token1_id = t1.id  WHERE l.state_id = ?;", (compare,)):
            old_total += row[3]
            if (row[4], row[5]) in contents:
                old = contents[(row[4], row[5])]
                contents[(row[4], row[5])] = [old[0] ,format_balance(old[1], get_perc_diff(
                    old[1], row[2])), format_money(old[2], get_perc_diff(old[2], row[3]))]
    for row in contents.items():
        r = row[1]
        if not isinstance(r[1],str):
            r[1] = format_balance(r[1])
        if not isinstance(r[2],str):
            r[2] = format_money(r[2])
        table.add_row(row[1])
    print("==== Liquidity Pool Balance ====")
    table.align = "l"
    print(table)
    total = format_money(total_val, get_perc_diff(old_total, total_val))
    print_table_summary(table, "Total", total)
    return (total_val, old_total)


def print_wallet_state(file, state, compare=None):
    (_,wallet,ts) = get_state_id(file,state)
    comparestr = ""
    if compare is not None:
        (_,old_wallet,old_ts) = get_state_id(file,state)
        wallet_str = ""
        if wallet != old_wallet:
            wallet_str = "for wallet {}".format(old_wallet)
        comparestr = " compared to state {} from {} {}".format(compare,old_ts,wallet_str)
    print("State {} from {} for wallet address {}{}".format(state, ts, wallet,comparestr))
    (total, old_total) = print_token_state(file, state, compare)
    (total2, old_total2) = print_liquidity_state(file, state, compare)
    print("=== Total wallet value: {:.2f} $ ({}) ===".format(
        total+total2, get_perc_diff(old_total+old_total2, total+total2)))


def list_states(file, wallet):
    con = sqlite3.connect(file)
    cur = con.cursor()
    if wallet is None:
        res = cur.execute("SELECT * FROM state")
    else:
        res = cur.execute(
            "SELECT * FROM state WHERE wallet_address = ?", (wallet,))
    table = from_db_cursor(res)
    print(table)
    con.close()


def drop_state(file, state):
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.execute('''PRAGMA foreign_keys = ON;''')
    cur.execute('DELETE FROM state WHERE id = ?', (state,))
    con.commit()
    con.close()


def drop_states_by_time(file, time_clause):
    con = sqlite3.connect(file)
    cur = con.cursor()
    cur.execute('''PRAGMA foreign_keys = ON;''')
    cur.execute('DELETE FROM state WHERE id NOT IN (SELECT id FROM state GROUP BY wallet_address, strftime(?,timestamp) HAVING MAX(timestamp) ORDER BY id)', (time_clause,))
    con.commit()
    con.close()

#  __  __ _
# |  \/  (_)
# | \  / |_ ___  ___
# | |\/| | / __|/ __|
# | |  | | \__ \ (__
# |_|  |_|_|___/\___|


def get_perc_diff(old, new):
    if old == 0.0 and new == 0.0:
        return "-"
    if old is None or old == 0.0:
        return "New"
    if new is None:
        return "-100%"
    diff = old-new
    out = "{:+.2f}%".format((diff/old)*100)

    if diff == 0.0:
        return "-"
    return out


def format_money(val, diff = None):
    if diff is None:
        if val < 1.0:
            return "{:.3g} $".format(val)
        return "{:.2f} $".format(val)
    if val < 1.0:
        return "{:.3g} $ ({})".format(val,diff)
    return "{:.2f} $ ({})".format(val,diff)

def format_balance(val, diff = None):
    if diff is None:
        return "{:.3g}".format(val)
    return "{:.3g} ({})".format(val,diff)



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


def fetch_coin(wallet, state_id):
    endpoint = "?module=account&action=balance&address={}".format(wallet)
    url = "{}{}".format(blockscout_url, endpoint)
    coin_response = requests.get(url)
    if(coin_response.ok):
        data = json.loads(coin_response.content)
        coin = data["result"]
        return coin
    else:
        print("Could not connect to {}".format(url))
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
        if tokens is None:
            tokens = []
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


db_file_helptext = "The SQLite DB file. Default: 'wallettools.sqlite'"
wallet_helptext = "Your xDai wallet address"
exchange_helptext = 'Uniswap V2 compatible exchange APIs to query. Default: Honeyswap API'


@cli.command()
@click.option('--wallet', help=wallet_helptext, required=True, multiple=True)
@click.option('--db', help=db_file_helptext, default=default_db)
@click.option('--exchange', help=exchange_helptext, multiple=True, default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
def update(wallet, db, exchange):
    """Fetches the current state of your wallet."""
    init_db(db)
    for w in wallet:
        fetch_db(db, format_wallet_address(w), exchange)


@cli.command()
@click.option('--wallet', help=wallet_helptext, required=True, multiple=True)
@click.option('--db', help=db_file_helptext, default=default_db)
@click.option('--exchange', help=exchange_helptext, multiple=True, default=["https://api.thegraph.com/subgraphs/name/1hive/uniswap-v2"])
@click.option('--fetch/--no-fetch', default=True, help='Fetch new data before displaying')
@click.option('--compare', help='A state to compare to, default last sate of wallet', type=int)
def show(wallet, db, exchange, fetch, compare):
    """Shows the last state of your wallet"""
    init_db(db)
    for w in wallet:
        w = format_wallet_address(w)
        if fetch:
            fetch_db(db, w, exchange)
        state = get_last_state_id(db, w)
        if compare is None:
            compare = get_previous_state_id(db, state)
        if state is None:
            print("Could not find any state for wallet address {}".format(w))
            return
        print_wallet_state(db, state, compare)
        print("\n\n")


@cli.command()
@click.option('--wallet', help=wallet_helptext, required=False)
@click.option('--db', help=db_file_helptext, default=default_db)
def states(wallet, db):
    """Shows all states in the database"""
    if wallet is not None:
        wallet = format_wallet_address(wallet)
    init_db(db)
    list_states(db, wallet)


@cli.command()
@click.option('--state', help='The state to view', required=True, type=int)
@click.option('--db', help=db_file_helptext, default=default_db)
@click.option('--compare', help='A state to compare to', type=int)
def state(state, db, compare):
    """Shows the wallet balance in a given historical state"""
    init_db(db)
    state_info = get_state_id(db, state)
    if state_info is None:
        print("Could not find any state with id {}".format(state_info))
        return
    print_wallet_state(db, state_info[0], compare)


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@cli.command()
@click.option('--db', help=db_file_helptext, default=default_db)
@click.option('--state', help='A specific state to prune', type=int)
@click.option('--time', help="Only keep the most recent states for a given time period. (e.g.: one state per wallet per hour)", type=click.Choice(['YEAR', 'MONTH', 'WEEK', 'DAY', 'HOUR'], case_sensitive=False))
@click.option('--yes', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to prune the states?')
def prune(db, state, time):
    """Prunes states depending on given options"""
    init_db(db)
    if state is not None:
        print("Pruning state {}".format(state))
        drop_state(db, state)
    if time is not None:
        print("Pruning states based on {}".format(time))
        time = time.upper()
        if time == "YEAR":
            drop_states_by_time(db, "%Y")
        elif time == "MONTH":
            drop_states_by_time(db, "%Y-%m")
        elif time == "WEEK":
            drop_states_by_time(db, "%Y-%W")
        elif time == "DAY":
            drop_states_by_time(db, "%Y-%m-%d")
        elif time == "HOUR":
            drop_states_by_time(db, "%Y-%m-%d-%H")


if __name__ == '__main__':
    cli()
