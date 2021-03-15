This python script is a tool I use to keep an overview over my finances on the xDai crypto currency chain.

# Usage / Features

## Token balance

To get an overview over all tokens (and their USD value) in a wallet you can use:

```bash
./wallettools.py tokens --wallet WALLET-ADDRESS [--exchange EXCHANGE-API-URL]
```

The exchange API can be any GraphQL endpoint of a Uniswap-V2 fork. (e.g.: Honeyswap, Bao-Swap, ...).
If no exchange is given, Honeyswap is used per default.

The script will then get all tokens from [Blockscout](https://blockscout.com/xdai/mainnet) and calculate their USD value using the given exchange.
This requires that the token is traded on the given exchange.

## Pool Liquidity

To summarize pool liquidity that you provide on multiple exchanges you can use

```bash
./wallettools.py pools --wallet WALLET-ADDRESS [--exchange EXCHANGE-API-URL]
```

As above the script will always check on Honeyswap. By using the `--exchange` argument multiple times you can specify additional exchanges to check.

## Wallet balance
To execute both of the above commands and sum up their results, you can use

```bash
./wallettools.py balance --wallet WALLET-ADDRESS [--exchange EXCHANGE-API-URL]
```
