#!/usr/bin/env python
#
# Code for dumping the bitcoin Berkeley db files in a human-readable format
#
from bsddb.db import *
import logging
import sys

from address import dump_addresses
from wallet import dump_wallet
from blocks import dump_blockindex
from transactions import dump_transactions

def determine_db_dir():
  import os
  import os.path
  import platform
  if platform.system() == "Darwin":
    return os.path.expanduser("~/Library/Application Support/Bitcoin/")
  elif platform.system() == "Windows":
    return os.path.join(os.environ['APPDATA'], "Bitcoin")
  return os.path.expanduser("~/.bitcoin")

def main():
  import optparse
  parser = optparse.OptionParser(usage="%prog [options]")
  parser.add_option("--wallet", action="store_true", dest="dump_wallet", default=False,
                    help="Print out contents of the wallet.dat file")
  parser.add_option("--blocks", action="store_true", dest="dump_blocks", default=False,
                    help="Print out contents of the blkindex.dat file")
  parser.add_option("--wallet-tx", action="store_true", dest="dump_wallet_tx", default=False,
                    help="Print transactions in the wallet.dat file")
  parser.add_option("--address", action="store_true", dest="dump_addr", default=False,
                    help="Print addresses in the addr.dat file")
  (options, args) = parser.parse_args()

  db_dir = determine_db_dir()

  db_env = DBEnv(0)
  r = db_env.open(db_dir,
                  (DB_CREATE|DB_INIT_LOCK|DB_INIT_LOG|DB_INIT_MPOOL|
                   DB_INIT_TXN|DB_THREAD|DB_PRIVATE|DB_RECOVER))

  if r is not None:
    logging.error("Couldn't open "+DB_DIR)
    sys.exit(1)

  if options.dump_wallet or options.dump_wallet_tx:
    dump_wallet(db_env, options.dump_wallet, options.dump_wallet_tx)

  if options.dump_addr:
    dump_addresses(db_env)

  if options.dump_blocks:
    dump_blockindex(db_env)

  db_env.close()

if __name__ == '__main__':
    main()
