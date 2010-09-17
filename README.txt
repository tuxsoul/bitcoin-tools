Run    dbdump.py --help    for usage.  Database files are opened read-only, but
you might want to backup your Bitcoin wallet.dat file just in case.

You must quit Bitcoin before reading the transactions, blocks, or address database files.

Requires the pycrypto library from  http://www.dlitz.net/software/pycrypto/
to translate public keys into human-friendly Bitcoin addresses.

Examples:

Print out  wallet keys and transactions:
  dbdump.py --wallet --wallet-tx

Print out the "genesis block" (the very first block in the proof-of-work block chain):
  dbdump.py --block=27edfeb3b3c3b72a57c460a0d7bfceaa98c0d8c59fbca196910fdc0800000000

Print out one of the transactions from my wallet:
  dbdump.py --transaction=c90a...9213

Print out all blocks involving transactions to the Bitcoin Faucet:
  dbdump.py --search-blocks=15VjRaDX9zpbA8LVnbrCAFzrVzN7ixHNsC

There's a special search term to look for non-standard transactions:
  dbdump.py --search-blocks=NONSTANDARD_CSCRIPTS
