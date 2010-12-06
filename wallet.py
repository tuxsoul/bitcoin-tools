#
# Code for parsing the wallet.dat file
#

from bsddb.db import *
import logging
import pdb
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

def parse_wallet(db, item_callback):
  kds = BCDataStream()
  vds = BCDataStream()

  for (key, value) in db.items():
    d = { }

    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_string()

    d["__key__"] = key
    d["__value__"] = value
    d["__type__"] = type

    try:
      if type == "tx":
        d["tx_id"] = kds.read_bytes(32)
        d.update(parse_WalletTx(vds))
      elif type == "name":
        d['hash'] = kds.read_string()
        d['name'] = vds.read_string()
      elif type == "version":
        d['version'] = vds.read_uint32()
      elif type == "setting":
        d['setting'] = kds.read_string()
        d['value'] = parse_setting(d['setting'], vds)
      elif type == "key":
        d['public_key'] = kds.read_bytes(kds.read_compact_size())
        d['private_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "wkey":
        d['public_key'] = kds.read_bytes(kds.read_compact_size())
        d['private_key'] = vds.read_bytes(vds.read_compact_size())
        d['created'] = vds.read_int64()
        d['expires'] = vds.read_int64()
        d['comment'] = vds.read_string()
      elif type == "defaultkey":
        d['key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "pool":
        d['n'] = kds.read_int64()
        d['nVersion'] = vds.read_int32()
        d['nTime'] = vds.read_int64()
        d['public_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "acc":
        d['account'] = kds.read_string()
        d['nVersion'] = vds.read_int32()
        d['public_key'] = vds.read_bytes(vds.read_compact_size())
      elif type == "acentry":
        d['account'] = kds.read_string()
        d['n'] = kds.read_uint64()
        d['nVersion'] = vds.read_int32()
        d['nCreditDebit'] = vds.read_int64()
        d['nTime'] = vds.read_int64()
        d['otherAccount'] = vds.read_string()
        d['comment'] = vds.read_string()
      else:
        print "Unknown key type: "+type
      
      item_callback(type, d)

    except Exception, e:
      print("ERROR parsing wallet.dat, type %s"%type)
      print("key data in hex: %s"%key.encode('hex_codec'))
      print("value data in hex: %s"%value.encode('hex_codec'))
  

def dump_wallet(db_env, print_wallet, print_wallet_transactions, transaction_filter):
  db = open_wallet(db_env)

  wallet_transactions = []

  def item_callback(type, d):
    if type == "tx":
      wallet_transactions.append( d )
    elif print_wallet:
      if type == "name":
        print("ADDRESS "+d['hash']+" : "+d['name'])
      elif type == "version":
        print("Version: %d"%(d['version'],))
      elif type == "setting":
        print(d['setting']+": "+str(d['value']))
      elif type == "key":
        print("PubKey "+ short_hex(d['public_key']) + " " + public_key_to_bc_address(d['public_key']) +
              ": PriKey "+ short_hex(d['private_key']))
      elif type == "wkey":
        print("WPubKey 0x"+ short_hex(d['public_key']) + " " + public_key_to_bc_address(d['public_key']) +
              ": WPriKey 0x"+ short_hex(d['private_key']))
        print(" Created: "+time.ctime(d['created'])+" Expires: "+time.ctime(d['expires'])+" Comment: "+d['comment'])
      elif type == "defaultkey":
        print("Default Key: 0x"+ short_hex(d['key']) + " " + public_key_to_bc_address(d['key']))
      elif type == "pool":
        print("Change Pool key %d: %s (Time: %s)"% (d['n'], public_key_to_bc_address(d['public_key']), time.ctime(d['nTime'])))
      elif type == "acc":
        print("Account %s (current key: %s)"%(d['account'], public_key_to_bc_address(d['public_key'])))
      elif type == "acentry":
        print("Move '%s' %d (other: '%s', time: %s, entry %d) %s"%
              (d['account'], d['nCreditDebit'], d['otherAccount'], time.ctime(d['nTime']), d['n'], d['comment']))
      else:
        print "Unknown key type: "+type

  parse_wallet(db, item_callback)

  if print_wallet_transactions:
    sortfunc = lambda t1, t2: t1['timeReceived'] < t2['timeReceived']
    for d in sorted(wallet_transactions, cmp=sortfunc):
      tx_value = deserialize_WalletTx(d)
      if len(transaction_filter) > 0 and re.search(transaction_filter, tx_value) is None: continue

      print("==WalletTransaction== "+long_hex(d['tx_id'][::-1]))
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

def rewrite_wallet(db_env, destFileName):
  db = open_wallet(db_env)

  db_out = DB(db_env)
  try:
    r = db_out.open(destFileName, "main", DB_BTREE, DB_CREATE)
  except DBError:
    r = True

  if r is not None:
    logging.error("Couldn't open %s."%destFileName)
    sys.exit(1)

  def item_callback(type, d):
    db_out.put(d["__key__"], d["__value__"])

  parse_wallet(db, item_callback)

  db_out.close()
  db.close()
