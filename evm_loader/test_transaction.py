from solana.rpc.api import Client
from solana.account import Account
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
from solana.sysvar import *
from solana.rpc.types import TxOpts
import unittest
import time
import os
import json
from hashlib import sha256
from spl.token.client import Token

import subprocess

import struct

from ecdsa import SigningKey, SECP256k1, VerifyingKey
from sha3 import keccak_256
import json
from eth_keys import keys


def unpack(data):
    ch = data[0]
    if (ch <= 0x7F):
        return (ch, data[1:])
    elif (ch == 0x80):
        return (None, data[1:])
    elif (ch <= 0xB7):
        l = ch - 0x80
        return (data[1:1+l].tobytes(), data[1+l:])
    elif (ch <= 0xBF):
        lLen = ch - 0xB7
        l = int.from_bytes(data[1:1+lLen], byteorder='little')
        return (data[1+lLen:1+lLen+l].tobytes(), data[1+lLen+l:])
    elif (ch == 0xC0):
        return ((), data[1:])
    elif (ch <= 0xF7):
        l = ch - 0xC0
        lst = list()
        sub = data[1:1+l]
        while len(sub):
            (item, sub) = unpack(sub)
            lst.append(item)
        return (lst, data[1+l:])
    else:
        lLen = ch - 0xF7
        l = int.from_bytes(data[1:1+lLen], byteorder='little')
        lst = list()
        sub = data[1+lLen:1+lLen+l]
        while len(sub):
            (item, sub) = unpack(sub)
            lst.append(item)
        return (lst, data[1+lLen+l:])

def pack(data):
    if data == None:
        return (0x80).to_bytes(1,'big')
    if isinstance(data, str):
        return pack(data.encode('utf8'))
    elif isinstance(data, bytes):
        if len(data) <= 55:
            return (len(data)+0x80).to_bytes(1,'big')+data
        else:
            l = len(data)
            lLen = (l.bit_length()+7)//8
            return (0xB7+lLen).to_bytes(1,'big')+l.to_bytes(lLen,'big')+data
    elif isinstance(data, int):
        if data < 0x80:
            return data.to_bytes(1,'big')
        else:
            l = (data.bit_length()+7)//8
            return (l + 0x80).to_bytes(1,'big') + data.to_bytes(l,'big')
        pass
    elif isinstance(data, list) or isinstance(data, tuple):
        if len(data) == 0:
            return (0xC0).to_bytes(1,'big')
        else:
            res = bytearray()
            for d in data:
                res += pack(d)
            l = len(res)
            if l <= 0x55:
                return (l + 0xC0).to_bytes(1,'big')+res
            else:
                lLen = (l.bit_length()+7)//8
                return (lLen+0xF7).to_bytes(1,'big') + l.to_bytes(lLen,'big') + res
    else:
        raise Exception("Unknown type {} of data".format(str(type(data))))

def getInt(a):
    if isinstance(a, int): return a
    if isinstance(a, bytes): return int.from_bytes(a, 'big')
    if a == None: return a
    raise Exception("Invalid convertion from {} to int".format(a))

class Trx:
    def __init__(self):
        self.nonce = None
        self.gasPrice = None
        self.gasLimit = None
        self.toAddress = None
        self.value = None
        self.callData = None
        self.v = None
        self.r = None
        self.s = None

    @classmethod
    def fromString(cls, s):
        t = Trx()
        (unpacked, data) = unpack(memoryview(s))
        (nonce, gasPrice, gasLimit, toAddress, value, callData, v, r, s) = unpacked
        t.nonce = getInt(nonce)
        t.gasPrice = getInt(gasPrice)
        t.gasLimit = getInt(gasLimit)
        t.toAddress = toAddress
        t.value = getInt(value)
        t.callData = callData
        t.v = getInt(v)
        t.r = getInt(r)
        t.s = getInt(s)
        return t
    
    def chainId(self):
        # chainid*2 + 35  xxxxx0 + 100011   xxxx0 + 100010 +1
        # chainid*2 + 36  xxxxx0 + 100100   xxxx0 + 100011 +1
        return (self.v-1)//2 - 17

    def __str__(self):
        return pack((
            self.nonce,
            self.gasPrice,
            self.gasLimit,
            self.toAddress,
            self.value,
            self.callData,
            self.v,
            self.r.to_bytes(32,'big') if self.r else None,
            self.s.to_bytes(32,'big') if self.s else None)
        ).hex()

    def get_msg(self, chainId=None):
        trx = pack((
            self.nonce,
            self.gasPrice,
            self.gasLimit,
            self.toAddress,
            self.value,
            self.callData,
            chainId or self.chainId(), None, None))
        return trx

    def hash(self, chainId=None):
        trx = pack((
            self.nonce,
            self.gasPrice,
            self.gasLimit,
            self.toAddress,
            self.value,
            self.callData,
            chainId or self.chainId(), None, None))
        return keccak_256(trx).digest()

    def sender(self):
        msgHash = self.hash()
        sig = keys.Signature(vrs=[1 if self.v%2==0 else 0, self.r, self.s])
        pub = sig.recover_public_key_from_msg_hash(msgHash)
        return pub.to_canonical_address().hex()

class JsonEncoder(json.JSONEncoder):
   def default(self, obj):
       if isinstance(obj, bytes):
           return obj.hex()
       return json.JSONEncoder.default(self.obj)


solana_url = os.environ.get("SOLANA_URL", "http://localhost:8899")
http_client = Client(solana_url)
# path_to_patched_solana = '../solana/target/debug/solana' #solana
path_to_patched_solana = '/home/dmitriy/cyber-core/solana/target/debug/solana'

def confirm_transaction(client, tx_sig):
    """Confirm a transaction."""
    TIMEOUT = 30  # 30 seconds  pylint: disable=invalid-name
    elapsed_time = 0
    while elapsed_time < TIMEOUT:
        sleep_time = 3
        if not elapsed_time:
            sleep_time = 7
            time.sleep(sleep_time)
        else:
            time.sleep(sleep_time)
        resp = client.get_confirmed_transaction(tx_sig)
        if resp["result"]:
#            print('Confirmed transaction:', resp)
            break
        elapsed_time += sleep_time
        if not resp["result"]:
            raise RuntimeError("could not confirm transaction: ", tx_sig)
    return resp



class SolanaCli:
    def __init__(self, url, acc):
        self.url = url
        self.acc = acc

    def call(self, arguments):
        cmd = '{} --keypair {} --url {} {}'.format(path_to_patched_solana, self.acc.get_path(), self.url, arguments)
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            import sys
            print("ERR: solana error {}".format(err))
            raise



class RandomAccaunt:
    def __init__(self, path=None):
        if path == None:
            self.make_random_path()
            print("New keypair file: {}".format(self.path))    
            self.generate_key()
        else:
            self.path = path
        self.retrieve_keys()
        print('New Public key:', self.acc.public_key())
        print('Private:', self.acc.secret_key())


    def make_random_path(self):
        import calendar;
        import time;
        ts = calendar.timegm(time.gmtime())
        self.path = str(ts) + '.json'
        time.sleep(1)
        

    def generate_key(self):
        cmd_generate = 'solana-keygen new --no-passphrase --outfile {}'.format(self.path)
        try:
            return subprocess.check_output(cmd_generate, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            import sys
            print("ERR: solana error {}".format(err))
            raise

    def retrieve_keys(self):
        with open(self.path) as f:
            d = json.load(f)
            self.acc = Account(d[0:32])

    def get_path(self):
        return self.path

    def get_acc(self):
        return self.acc



class EvmLoader:
    def __init__(self, solana_url, acc, programId=None):
        if programId == None:
            print("Load EVM loader...")
            cli = SolanaCli(solana_url, acc)
            contract = 'target/bpfel-unknown-unknown/release/evm_loader.so'
            result = json.loads(cli.call('deploy {}'.format(contract)))
            programId = result['programId']
        EvmLoader.loader_id = programId
        # EvmLoader.loader_id = "3qEJUEkcbP5PEWzRxRYpa6yfVBm5yZmHkz7TzjRzUPhP"
        print("Done\n")

        self.solana_url = solana_url
        self.loader_id = EvmLoader.loader_id
        self.acc = acc
        print("Evm loader program: {}".format(self.loader_id))


    def deploy(self, contract):
        cli = SolanaCli(self.solana_url, self.acc)
        output = cli.call("deploy --use-evm-loader {} {}".format(self.loader_id, contract))
        print(type(output), output)
        result = json.loads(output.splitlines()[-1])
        return result['programId']


    def createEtherAccount(self, ether):
        cli = SolanaCli(self.solana_url, self.acc)
        output = cli.call("create-ether-account {} {} 1".format(self.loader_id, ether.hex()))
        result = json.loads(output.splitlines()[-1])
        return result["solana"]


    def ether2program(self, ether):
        cli = SolanaCli(self.solana_url, self.acc)
        output = cli.call("create-program-address {} {}".format(ether.hex(), self.loader_id))
        items = output.rstrip().split('  ')
        return (items[0], int(items[1]))

    def checkAccount(self, solana):
        info = http_client.get_account_info(solana)
        print("checkAccount({}): {}".format(solana, info))

    def deployChecked(self, location):
        from web3 import Web3
        creator = solana2ether("6ghLBF2LZAooDnmUMVm8tdNK6jhcAQhtbQiC7TgVnQ2r")
        with open(location, mode='rb') as file:
            fileHash = Web3.keccak(file.read())
            ether = bytes(Web3.keccak(b'\xff' + creator + bytes(32) + fileHash)[-20:])
        program = self.ether2program(ether)
        info = http_client.get_account_info(program[0])
        if info['result']['value'] is None:
            return self.deploy(location)
        elif info['result']['value']['owner'] != self.loader_id:
            raise Exception("Invalid owner for account {}".format(program))
        else:
            return {"ethereum": ether.hex(), "programId": program[0]}


def getBalance(account):
    return http_client.get_balance(account)['result']['value']

def solana2ether(public_key):
    from web3 import Web3
    return bytes(Web3.keccak(bytes(PublicKey(public_key)))[-20:])


class EvmLoaderTestsNewAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acc = RandomAccaunt()
        # cls.acc = RandomAccaunt('1613073922.json')
        if getBalance(cls.acc.get_acc().public_key()) == 0:
            print("request_airdrop for ", cls.acc.get_acc().public_key())
            cli = SolanaCli(solana_url, cls.acc)
            cli.call('airdrop 1000000')
            # tx = http_client.request_airdrop(cls.acc.get_acc().public_key(), 100000)
            # confirm_transaction(http_client, tx['result'])
            # balance = http_client.get_balance(cls.acc.get_acc().public_key())['result']['value']
            print("Done\n")
            
        cls.loader = EvmLoader(solana_url, cls.acc)
        # cls.loader = EvmLoader(solana_url, cls.acc, '3ZxexPKTYhrjdBvxUBhTnH842iJLJ2t9qDUGQbNUeMvM')
        cls.evm_loader = cls.loader.loader_id
        print("evm loader id: ", cls.evm_loader)
        # cls.owner_contract = cls.loader.deploy('evm_loader/hello_world.bin')
        # cls.owner_contract = "GUvbhZrRccxTd6yCX694iMxN5wz7mAUTiTYZfh2YCGWv"
        # print("contract id: ", cls.owner_contract)

        # cls.caller_ether = solana2ether(cls.acc.get_acc().public_key())
        # (cls.caller, cls.caller_nonce) = cls.loader.ether2program(cls.caller_ether)

        # if getBalance(cls.caller) == 0:
        #     print("Create caller account...")
        #     caller_created = cls.loader.createEtherAccount(solana2ether(cls.acc.get_acc().public_key()))
        #     print("Done\n")

        # print('Account:', cls.acc.get_acc().public_key(), bytes(cls.acc.get_acc().public_key()).hex())
        # print("Caller:", cls.caller_ether.hex(), cls.caller_nonce, "->", cls.caller, "({})".format(bytes(PublicKey(cls.caller)).hex()))

    # def test_parse_tx(self):
    #     call_hello = bytearray.fromhex("a1f86c018522ecb25c0082520894a090e606e30bd747d4e6245a1517ebe430f0057e880340c0086a5cbe008025a0e213a2a87b050644f9c982144fa762132bbc00b9ac63d168d68146e300de6b4ba059dbbae6d190d820ddde818a98204232194eb6d27226190b4c0be82480d6a735")
    #     trx = Transaction().add(
    #         TransactionInstruction(program_id=self.evm_loader, data=call_hello, keys=[
    #             AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),
    #         ]))
    #     result = http_client.send_transaction(trx, self.acc.get_acc())
    #     print(result)

    def test_check_tx(self):    
        trx = "0xf86c258520d441420082520894d8587a2fd6c30dd5c70f0630f1a635e4ae6ae47188043b93e2507e80008025a00675d0de7873f2c77a1c7ab0806cbda67ea6c25303ca7a80c211af97ea202d6aa022eb61dbc3097d7a8a4b142fd7f3c03bd8320ad02d564d368078a0a5fe227199"
        # trx = '0xf87202853946be1c0082520894c1566af4699928fdf9be097ca3dc47ece39f8f8e880de0b6b3a7640000808602e92be91e85a06f350382938df92b987681de78d81f0490ee1d26b18ea968ae42ee4a800711a6a0641672e91b735bd6badd2c51b6a6ecdcd740b78c8bf581aa3f1431cd0f8c02f3'
        
        _trx = Trx.fromString(bytearray.fromhex(trx[2:]))
        
        raw_msg = _trx.get_msg()
        msgHash = _trx.hash()
        sig = keys.Signature(vrs=[1 if _trx.v%2==0 else 0, _trx.r, _trx.s])
        pub = sig.recover_public_key_from_msg_hash(msgHash)
                
        data = bytearray.fromhex("a2")
        data += struct.pack("<I", len(raw_msg))
        data += raw_msg
        data += sig.to_bytes()
        data += pub.to_canonical_address()

        data1 = bytearray.fromhex("a2")
        data1 += struct.pack("<I", len(msgHash))
        data1 += msgHash
        data1 += sig.to_bytes()
        data1 += pub.to_canonical_address()
               
        trx = Transaction().add(
            TransactionInstruction(program_id=self.evm_loader, data=data, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),   
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),                
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=data1, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),   
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),                
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=data, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),   
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),                
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=data1, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),   
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),                
            ]))
        result = http_client.send_transaction(trx, self.acc.get_acc())


if __name__ == '__main__':
    unittest.main()
