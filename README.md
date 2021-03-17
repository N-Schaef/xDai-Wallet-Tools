This python script is a tool I use to keep an overview over my finances on the xDai crypto currency chain.

# Installation

This script requires click and prettytables.
These requirements can be installed using:

```bash
pip3 install -r requirements.txt
```

# Usage / Features

## Wallet balance

To get an overview over your wallet balance and liquidities in exchanges use

```bash
./wallettools.py show --wallet WALLET-ADDRESS [--exchange EXCHANGE-API-URL] [--db SQLite-FILE ] [--fetch/--no-fetch]
```

The exchange API can be any GraphQL endpoint of a Uniswap-V2 fork. (e.g.: Honeyswap, Bao-Swap, ...).
If no exchange is given, Honeyswap is used per default.

The script will then get all tokens from [Blockscout](https://blockscout.com/xdai/mainnet) and calculate their USD value using the given exchange.
This requires that the token is traded on the given exchange.
By using the `--exchange` argument multiple times you can specify additional exchanges to check.


