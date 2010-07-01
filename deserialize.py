#
# Deserialize bitcoin objects from BCDataStreams
#

from BCDataStream import *
from enumeration import Enumeration
from base58 import public_key_to_bc_address, hash_160_to_bc_address
import socket
import time
from util import short_hex

def deserialize_CAddress(vds):
  version = vds.read_int32()
  t = vds.read_uint32()
  nServices = vds.read_uint64()
  vds.read_bytes(12) # pchReserved
  ip = socket.inet_ntoa(vds.read_bytes(4))
  port = vds.read_uint16()
  return ip+":"+str(port)

def deserialize_setting(setting, vds):
  if setting[0] == "f":  # flag (boolean) settings
    return str(vds.read_boolean())
  elif setting[0:4] == "addr": # CAddress
    return deserialize_CAddress(vds)
  elif setting == "nTransactionFee":
    return vds.read_int64()
  elif setting == "nLimitProcessors":
    return vds.read_int32()
  return 'unknown setting'

def deserialize_TxIn(vds):
  prevout_hash = vds.read_bytes(32)
  prevout_n = vds.read_uint32()
  scriptSig = vds.read_bytes(vds.read_compact_size())
  sequence = vds.read_uint32()
  if prevout_hash == "\x00"*32:
    result = "TxIn: COIN GENERATED"
    result += " coinbase:"+scriptSig.encode('hex_codec')
  else:
    result = "TxIn: prev("+short_hex(prevout_hash)+":"+str(prevout_n)+")"
    pk = extract_public_key(scriptSig)
    result += " pubkey: "+pk
    result += " sig: "+decode_script(scriptSig)
  if sequence < 0xffffffff: result += " sequence: "+hex(sequence)
  return result
def deserialize_TxOut(vds):
  value = vds.read_int64()
  scriptPubKey = vds.read_bytes(vds.read_compact_size())
  result =  "TxOut: value: %.2f"%(value/1.0e8,)
  pk = extract_public_key(scriptPubKey)
  result += " pubkey: "+pk
  result += " Script: "+decode_script(scriptPubKey)
  return result
def deserialize_Transaction(vds):
  version = vds.read_int32()
  n_vin = vds.read_compact_size()
  txIn = []
  for i in xrange(n_vin):
    txIn.append(deserialize_TxIn(vds))
  n_vout = vds.read_compact_size()
  txOut = []
  for i in xrange(n_vout):
    txOut.append(deserialize_TxOut(vds))
  lockTime = vds.read_uint32()
  result = "%d tx in, %d out\n"%(n_vin, n_vout)
  result += str(txIn)+"\n"
  result += str(txOut)
  return result
def deserialize_MerkleTx(vds):
  result = deserialize_Transaction(vds)
  hashBlock = vds.read_bytes(32)
  n_merkleBranch = vds.read_compact_size()
  merkleBranch = vds.read_bytes(32*n_merkleBranch)
  nIndex = vds.read_int32()
  result = "Merkle hashBlock: "+short_hex(hashBlock)+"\n" + result
  return result
def deserialize_WalletTx(vds):
  result = deserialize_MerkleTx(vds)
  n_vtxPrev = vds.read_compact_size()
  vtxPrev = []
  for i in xrange(n_vtxPrev):
    vtxPrev.append(deserialize_MerkleTx(vds))
  mapValue = {}
  n_mapValue = vds.read_compact_size()
  for i in xrange(n_mapValue):
    key = vds.read_string()
    value = vds.read_string()
    mapValue[key] = value
  n_orderForm = vds.read_compact_size()
  orderForm = []
  for i in xrange(n_mapValue):
    first = vds.read_string()
    second = vds.read_string()
    orderForm.append( (first, second) )
  timeReceivedIsTxTime = vds.read_uint32()
  timeReceived = vds.read_uint32()
  fromMe = vds.read_boolean()
  spent = vds.read_boolean()
  result += "\n"+" mapValue:"+str(mapValue)
  result += "\n"+" orderForm:"+str(orderForm)
  result += "\n"+" timeReceived:"+time.ctime(timeReceived)+" fromMe:"+str(fromMe)+" spent:"+str(spent)
  return (timeReceived, result)

def deserialize_Block(vds):
  version = vds.read_int32()
  hashPrev = vds.read_bytes(32)
  hashMerkleRoot = vds.read_bytes(32)
  nTime = vds.read_uint32()
  nBits = vds.read_uint32()
  nNonce = vds.read_uint32()
  nTransactions = vds.read_compact_size()
  result = "Time: "+time.ctime(nTime)
  result += "\nPrevious block: "+hashPrev.encode('hex_codec')
  result += "\n%d transactions:\n"%(nTransactions,)
  for i in range(0, nTransactions):
    result += deserialize_Transaction(vds)+"\n"
  return result

opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    ("OP_SINGLEBYTE_END", 0xF0),
    ("OP_DOUBLEBYTE_BEGIN", 0xF000),
    "OP_PUBKEY", "OP_PUBKEYHASH",
    ("OP_INVALIDOPCODE", 0xFFFF),
])

def script_GetOp(bytes):
  i = 0
  while i < len(bytes):
    vch = None
    opcode = ord(bytes[i])
    i += 1
    if opcode >= opcodes.OP_SINGLEBYTE_END:
      opcode <<= 8
      opcode |= bytes[i]
      i += 1

    if opcode <= opcodes.OP_PUSHDATA4:
      nSize = opcode
      if opcode == opcodes.OP_PUSHDATA1:
        nSize = ord(bytes[i])
        i += 1
      elif opcode == opcodes.OP_PUSHDATA2:
        nSize = unpack_from('<H', bytes, i)
        i += 2
      elif opcode == opcodes.OP_PUSHDATA4:
        nSize = unpack_from('<I', bytes, i)
        i += 4
      vch = bytes[i:i+nSize]
      i += nSize

    yield (opcode, vch)

def script_GetOpName(opcode):
  return (opcodes.whatis(opcode)).replace("OP_", "")

def decode_script(bytes):
  result = ''
  for (opcode, vch) in script_GetOp(bytes):
    if len(result) > 0: result += " "
    if opcode <= opcodes.OP_PUSHDATA4:
      result += "%d:"%(opcode,)
      result += short_hex(vch)
    else:
      result += script_GetOpName(opcode)
  return result

def match_decoded(decoded, to_match):
  if len(decoded) != len(to_match):
    return False;
  for i in range(len(decoded)):
    if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4:
      continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
    if to_match[i] != decoded[i][0]:
      return False
  return True

def extract_public_key(bytes):
  decoded = [ x for x in script_GetOp(bytes) ]

  # non-generated TxIn transactions push a signature
  # (seventy-something bytes) and then their public key
  # (65 bytes) onto the stack:
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[1][1])

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[0][1])

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[2][1])

  return "(None)"
