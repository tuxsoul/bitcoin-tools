#
# Code for parsing the wallet.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
import re
import sys
import time

from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex, long_hex
from deserialize import *

def open_wallet(db_env):
  db = DB(db_env)
  try:
    r = db.open("wallet.dat", "main", DB_BTREE, DB_THREAD|DB_RDONLY)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open wallet.dat/main. Try quitting Bitcoin and running this again.")
    sys.exit(1)
  
  return db

def dump_wallet(db_env, print_wallet, print_wallet_transactions, transaction_filter):
  db = open_wallet(db_env)

  kds = BCDataStream()
  vds = BCDataStream()

  wallet_transactions = []

  for (key, value) in db.items():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "tx":
      tx_id = kds.read_bytes(32)
      (when, value) = deserialize_WalletTx(vds)
      wallet_transactions.append( (when, tx_id, value) )
      continue

    if not print_wallet:
      continue

    if type == "name":
      hash = kds.read_string()
      name = vds.read_string()
      print("ADDRESS "+hash+" : "+name)
    elif type == "version":
      version = vds.read_uint32()
      print("Version: %d"%(version,))
    elif type == "setting":
      setting = kds.read_string()
      value = deserialize_setting(setting, vds)
      print(setting+": "+str(value))
    elif type == "key":
      public_key = kds.read_bytes(kds.read_compact_size())
      private_key = vds.read_bytes(vds.read_compact_size())
      print("PubKey "+ short_hex(public_key) + " " + public_key_to_bc_address(public_key) +
            ": PriKey "+ short_hex(private_key))
    elif type == "wkey":
      public_key = kds.read_bytes(kds.read_compact_size())
      private_key = vds.read_bytes(vds.read_compact_size())
      created = vds.read_int64()
      expires = vds.read_int64()
      comment = vds.read_string()
      print("WPubKey 0x"+ short_hex(public_key) + " " + public_key_to_bc_address(public_key) +
            ": WPriKey 0x"+ short_hex(private_key))
      print(" Created: "+time.ctime(created)+" Expires: "+time.ctime(expires)+" Comment: "+comment)
    elif type == "defaultkey":
      key = vds.read_bytes(vds.read_compact_size())
      print("Default Key: 0x"+ short_hex(key) + " " + public_key_to_bc_address(key))
    elif type == "pool":
      n = kds.read_int64()
      nVersion = vds.read_int32()
      nTime = vds.read_int64()
      public_key = vds.read_bytes(vds.read_compact_size())
      print("Change Pool key %d: %s (Time: %s)"% (n, public_key_to_bc_address(public_key), time.ctime(nTime)))
    elif type == "acc":
      account = kds.read_string()
      nVersion = vds.read_int32()
      public_key = vds.read_bytes(vds.read_compact_size())
      print("Account %s (current key: %s)"%(account, public_key_to_bc_address(public_key)))
    elif type == "acentry":
      account = kds.read_string()
      n = kds.read_uint64()
      nVersion = vds.read_int32()
      nCreditDebit = vds.read_int64()
      nTime = vds.read_int64()
      otherAccount = vds.read_string()
      comment = vds.read_string()
      print("Move '%s' %d (other: '%s', time: %s, entry %d) %s"%
            (account, nCreditDebit, otherAccount, time.ctime(nTime), n, comment))
    else:
      print "Unknown key type: "+type

  if print_wallet_transactions:
    for (t, tx_id, tx_value) in sorted(wallet_transactions, key=itemgetter(0)):
      if len(transaction_filter) > 0 and re.search(transaction_filter, tx_value) is None: continue

      print("==WalletTransaction== "+long_hex(tx_id[::-1]))
      print(tx_value)

  db.close()

def dump_accounts(db_env):
  db = open_wallet(db_env)

  kds = BCDataStream()
  vds = BCDataStream()

  accounts = set()

  for (key, value) in db.items():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    if type == "acc":
      accounts.add(kds.read_string())
    elif type == "name":
      accounts.add(vds.read_string())
    elif type == "acentry":
      accounts.add(kds.read_string())
      # Note: don't need to add otheraccount, because moves are
      # always double-entry

  for name in sorted(accounts):
    print(name)

  db.close()
