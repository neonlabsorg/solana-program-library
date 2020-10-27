# TO run this test, use default solana's ./run.sh, but to spl-genesis-args.sh add:
# --bpf-program MetamaskW1111111111111111111111111111111111 BPFLoader1111111111111111111111111111111111 metamask-wrapper.so 

import time
import unittest
import json
from typing import NamedTuple
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.account import Account
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
from solana._layouts.shared import PUBLIC_KEY_LAYOUT, RUST_STRING_LAYOUT
from solana.sysvar import SYSVAR_RENT_PUBKEY
from nacl import public
import base58
import base64
import hashlib
from construct import Bytes, Int8ul, Int32ul, Int64ul, Pass  # type: ignore
from construct import Struct as cStruct
from spl.token.client import Token
import random

from eth_keys import keys as eth_keys

import wrapper
from wrapper import create_program_address, EthereumAddress

http_client = Client("http://localhost:8899")
memo_program = 'Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo'
token_program = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
metamask_program = '9aBMysdxZHW5BFZQiCkxRodjtXixydzBk7uDyJzFeyYX'
wrapper_program = 'CpB6wXiDrDohn9jAcXLbKxgcuAnwuAeATqcuXmHhnnBH'
system_id = '11111111111111111111111111111111'

CREATE_ACCOUNT_LAYOUT = cStruct(
    "instruction" / Int32ul,
    "lamports" / Int64ul,
    "space" / Int64ul,
    "owner" / PUBLIC_KEY_LAYOUT,
)
ALLOCATE_WITH_SEED_LAYOUT = cStruct(
    "instruction" / Int32ul,
    "base" / PUBLIC_KEY_LAYOUT,
    "seed" / RUST_STRING_LAYOUT,
    "space" / Int64ul,
    "owner" / PUBLIC_KEY_LAYOUT,
)
INITIALIZE_TOKEN_LAYOUT = cStruct(
    "instruction" / Int8ul,
)

TRANSFER_LAYOUT = cStruct(
    "instruction" / Int8ul,
    "amount" / Int64ul,
    "nonce" / Int8ul,
    "eth_token" / Bytes(20),
    "eth_acc" / Bytes(20),
)

INITIALIZE_ACCOUNT_LAYOUT = cStruct(
    "instruction" / Int8ul,
    "account" / PUBLIC_KEY_LAYOUT,
    "eth_acc" / Bytes(20),
    "nonce" / Int8ul,
)

INITIALIZE_AUTH_LAYOUT = cStruct(
    "instruction" / Int8ul,
    "account" / PUBLIC_KEY_LAYOUT,
    "eth_token" / Bytes(20),
    "eth_acc" / Bytes(20),
    "nonce" / Int8ul,
)

INITIALIZE_BALANCE_LAYOUT = cStruct(
    "instruction" / Int8ul,
    "eth_token" / Bytes(20),
    "eth_acc" / Bytes(20),
    "nonce" / Int8ul,
)

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


class SolanaTests(unittest.TestCase):
    version_recommended = '1.3.14'

    # such UI design is better visible than warnings.warn
    @classmethod
    def warn(cls, *arg):
        print('')
        print('(!) W A R N I N G ! ! !')
        print(*arg)
        print('')

    @classmethod
    def checkVersion(cls):
        print("Recommended Solana version: {'solana-core': '%s'}" % (cls.version_recommended))
        resp = http_client.get_version()['result']
        print('Solana version: %s' % (resp))
        if resp.get('solana-core', 'unknown').split()[0] == cls.version_recommended:
            print('Version is OK')
        else:
            cls.warn('Solana version is not matching recommended one, so API can differ and throw unknown errors!')

    @classmethod
    def checkProgramInstalled(cls, program_id):
        resp = http_client.get_account_info(PublicKey(program_id))['result']
        assert resp['value'] != None, 'Solana instance hasn\'t %s program installed' % program_id 

    @classmethod
    def setUpClass(cls):
        cls.checkVersion()
        #cls.checkProgramInstalled(memo_program)
        cls.checkProgramInstalled(token_program)
        #cls.checkProgramInstalled(metamask_program)

        cls.acc = Account(b'\xdc~\x1c\xc0\x1a\x97\x80\xc2\xcd\xdfn\xdb\x05.\xf8\x90N\xde\xf5\x042\xe2\xd8\x10xO%/\xe7\x89\xc0<')
        print('Account:', cls.acc.public_key())
        print('Private:', cls.acc.secret_key())
        balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        if balance == 0:
            tx = http_client.request_airdrop(cls.acc.public_key(), 10*10**9)
            confirm_transaction(http_client, tx['result'])
            balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        print('Balance:', balance)

        cls.wrapper = wrapper.WrapperProgram(http_client, wrapper_program)

    #def test_send_memo(self):
    #    keys = [
    #        AccountMeta(pubkey = self.acc.public_key(), is_signer=True, is_writable=False)
    #    ]
    #    data = 'Hello world'.encode('utf8')
    #    trx = Transaction().add(
    #        TransactionInstruction(keys=keys, program_id=memo_program, data=data))
    #    result = http_client.send_transaction(trx, self.acc)
    #    print('Send transaction result:', result)
    #    self.assertTrue('result' in result)
    #    confirm_transaction(http_client, result['result'])
    #    print("Confirmed")

    def test_ethereum_address(self):
        address = EthereumAddress.random()
        print(address)
        print(bytes(address).hex())
        print(address.private)

    def test_metamask(self):
        keys = [
            AccountMeta(pubkey = self.acc.public_key(), is_signer=False, is_writable=True),
            AccountMeta(pubkey = self.acc.public_key(), is_signer=False, is_writable=True)
        ]
        initializeData = INITIALIZE_TOKEN_LAYOUT.build(dict(
            instruction=0 # Initialize
        ))
        trx = Transaction().add(
            TransactionInstruction(keys=keys, program_id=metamask_program, data=initializeData))
        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])
        print("Confirmed")

    def test_create_program_address(self):
        program = '9ejTxeQaXBpgsJ9HN91TbLKXK3JdQEFgVa1eBF4ZbQcP'
        eth_token = bytearray.fromhex('59a449cd7fd8fbcf34d103d98f2c05245020e35c')
        eth_acc = bytearray.fromhex('c1566af4699928fdf9be097ca3dc47ece39f8f8e')
        (account, nonce) = create_program_address([eth_token, eth_acc], program)

    def test_metamask_init_account(self):
        # token returned from spl-token create-token
        token=PublicKey('AjQhwKQDGQV8CUfGhx59uesyXMk5XmYTuiLJzY9aFcno')
        eth_token = EthereumAddress.random()
        
        print('init_account:', token, eth_token)

        trx = Transaction().add(
            self.wrapper.initializeAccount(token, eth_token, self.acc.public_key()))
        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])

        # Check saved data about account
        info = self.wrapper.getAccountInfo(eth_token)
        self.assertEqual(info.account, token)

    def test_metamask_init_auth(self):
        # token returned from spl-token create-token
        account=PublicKey('Ajr1xT5FZtJuTq5jB6fgeYBxHoBrS4Bo1aCeBAcrYLpi')
        eth_token = EthereumAddress.random()
        eth_acc = EthereumAddress.random()

        print('init_authority:', account, eth_token, eth_acc)

        trx = Transaction().add(
            self.wrapper.initializeAuthority(account, eth_token, eth_acc, self.acc.public_key()))

        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])

        # Check saved data about account
        info = http_client.get_account_info(account_info)['result']['value']
        self.assertEqual(info['owner'], wrapper_program)
        self.assertEqual(info['data'][1], 'base64')
        data = base64.b64decode(info['data'][0])
        self.assertEqual(len(data), 72)
        acc = base58.b58encode(data[0:32]).decode('utf8')
        self.assertEqual(acc, str(account))

    def test_initialize_environment(self):
        token = Token.create_mint(
                http_client,
                self.acc,
                self.acc.public_key(),   # mint_authority 
                6,
                PublicKey(token_program), skip_confirmation=True)
        print('Created token:', token.pubkey)

        eth_token = EthereumAddress.random()
        print('Assign token to:', eth_token, self.wrapper.program_address([bytes(eth_token)]))
        trx = Transaction().add(
            self.wrapper.initializeToken(token.pubkey, eth_token, self.acc.public_key()))
        http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=True))

        balances = []
        for acc in ('0x324726CA9954Ed9bd567a62ae38a7dD7B4EaAD0e',    # 63def313b2ebdde0d09b0c0d1baaf8d2326f1598fd4a1e3e7c5927551bb1b496
                    '0x50B41b481f04ac2949C9Cc372b8F502Aa35bDddF',    # f8a2bdb9d447a61d15cfe53a5d6c63aa9e3d7ad279aef8d12bb44654ec358962
                    '0xB937AD32debAFa742907D83Cb9749443160DE0C4',    # fd124f967fc71ba7054bbef1376cf7ee3615b30265e3d81517129c4b21edce41
                    ):
            eth_acc = EthereumAddress(acc)
            (owner,nonce) = self.wrapper.program_address([bytes(eth_token), bytes(eth_acc)])

            account = token.create_account(owner, skip_confirmation=True)
            print('Create auth:', eth_acc, (owner,nonce), 'for', account)
            trx = Transaction()
            trx.add(self.wrapper.initializeAccount(eth_acc, self.acc.public_key()))
            trx.add(self.wrapper.initializeBalance(account, eth_token, eth_acc, self.acc.public_key()))
            result = http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=True))

            balances.append((account, random.randint(10**6, 1234*10**6),))
        confirm_transaction(http_client, result['result'])

        for (account, amount) in balances:
            result = token.mint_to(account, self.acc, amount)
        confirm_transaction(http_client, result['result'])

        for (account, amount) in balances:
            response = token.get_balance(account)
            print('Balance:', account, response['result']['value']['uiAmount'])
            self.assertEqual(amount, int(response['result']['value']['amount']))


    def test_transfer_lamports(self):
        eth_acc = EthereumAddress('0x324726CA9954Ed9bd567a62ae38a7dD7B4EaAD0e')
        balance = self.wrapper.getLamports(eth_acc)
        eth_tx_invalid = bytearray.fromhex('010203')
        eth_tx = bytearray.fromhex('f86b808503bfa2810082520894454c5477a55486afc43f069b2ee14246f6943e5e870e35fa931a00008078a0ce610aa6cf323602e3456d97481caee71c75b43aa5abb52740fc0bdcea50501ea0120796bc1e87e74f50a7bac5323b1c91564e891fd4a4e322888d90855ad5a701')

        trx = Transaction().add(
            self.wrapper.transferLamports(eth_acc, '6ghLBF2LZAooDnmUMVm8tdNK6jhcAQhtbQiC7TgVnQ2r', 1, eth_tx_invalid))
        try:
            result = http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=False))
            self.assertFalse('result' in result)
        except:
            pass

        trx = Transaction().add(
            self.wrapper.transferLamports(eth_acc, '6ghLBF2LZAooDnmUMVm8tdNK6jhcAQhtbQiC7TgVnQ2r', 1, eth_tx))
        result = http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=False))
        print('result:', result)

        self.assertEqual(balance-1, self.wrapper.getLamports(eth_acc))


    def test_metamask_init_balance(self):
        # token returned from spl-token create-token
        account=PublicKey('Ajr1xT5FZtJuTq5jB6fgeYBxHoBrS4Bo1aCeBAcrYLpi')
        mint=PublicKey('AjQhwKQDGQV8CUfGhx59uesyXMk5XmYTuiLJzY9aFcno')
        eth_token = bytearray.fromhex('c80102fd2d3d1be86823dd36f9c783ad0ee7d898')
        eth_token = bytearray.fromhex('4f0cefe10449ce29a70483d828b52d17bc73151c')
        eth_acc = bytearray.fromhex('c1566af4699928fdf9be097ca3dc47ece39f8f8e')
        (account_info, nonce) = create_program_address([eth_token, eth_acc], wrapper_program)
        print("Account_info:", account_info)

        print('Get minimum balance for rent exemption:', http_client.get_minimum_balance_for_rent_exemption(165))

        data = INITIALIZE_BALANCE_LAYOUT.build(dict(
            instruction=2,
            eth_token=eth_token,
            eth_acc=eth_acc,
            nonce=nonce,
        ))
        print('INITIALIZE_AUTH_LAYOUT:', data.hex())
        trx = Transaction().add(
            TransactionInstruction(program_id=wrapper_program, data=data, keys=[
                AccountMeta(pubkey=account_info, is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
                AccountMeta(pubkey=token_program, is_signer=False, is_writable=False),
                AccountMeta(pubkey=system_id, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=True),
            ])
        )

        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])

    def test_get_account(self):
        eth_token = '59a449cd7fd8fbcf34d103d98f2c05245020e35c'
        eth_acc = '46e7129d7ed2bdd5f7afb793fd085909468f52c1'
        program = wrapper.WrapperProgram(wrapper_program)
        accountInfo = program.getAccountInfo(eth_token, eth_acc);
        print('Account info:', accountInfo)

        balance = http_client.get_token_account_balance(accountInfo.account)
        print(balance)

    def test_get_decimals(self):
        eth_token = '59a449cd7fd8fbcf34d103d98f2c05245020e35c'
        #(token_info, nonce) = create_program_address([eth_token], wrapper_program)

        program = wrapper.WrapperProgram(wrapper_program)
        tokenInfo = program.getTokenInfo(eth_token)
        print(tokenInfo)

#        mint = http_client.get_account_info(tokenInfo.token)['result']['value']
#        print(mint)
#        self.assertEqual(mint['owner'], token_program)
#        mint_data = base64.b64decode(mint['data'][0])
#        print('mint_data:', mint_data.hex())
#        self.assertEqual(len(mint_data), 82)
#        decimals = int.from_bytes(mint_data[36+8:36+8+1], "little")
#        print('decimals:', decimals)
#        self.assertEqual(decimals, 9)

    def test_send_transfer(self):
        eth_token = bytearray.fromhex('4f0cefe10449ce29a70483d828b52d17bc73151c')
        eth_acc = bytearray.fromhex('c1566af4699928fdf9be097ca3dc47ece39f8f8e')
        # authority derived from create_program_address(eht_token, eth_acc, nonce)
        (authority, nonce) = create_program_address([eth_token, eth_acc], wrapper_program)
        # source should be owned by authority
#        source = 'EuFzBEkvXUUFvMxjqq3E34e711ydTu6YrqESuNg4qNC5'
        source = authority
        destination = 'EV6VidfoaoHDoT4sUCNQz96us2YAumqXo9ZJ4PQBVLjJ'
        # d2040000 01 59a449cd7fd8fbcf34d103d98f2c05245020e35b c1566af4699928fdf9be097ca3dc47ece39f8f8e
        eth_tx = bytearray.fromhex('f86b808503bfa2810082520894454c5477a55486afc43f069b2ee14246f6943e5e870e35fa931a00008078a0ce610aa6cf323602e3456d97481caee71c75b43aa5abb52740fc0bdcea50501ea0120796bc1e87e74f50a7bac5323b1c91564e891fd4a4e322888d90855ad5a701')

        print('authority:', authority, nonce)

        data = TRANSFER_LAYOUT.build(dict(
            instruction=3,
            amount=1234,
            nonce=nonce,
            eth_token=eth_token,
            eth_acc=eth_acc,
            eth_tx=eth_tx))
        print('TRANSFER_LAYOUT:', data.hex())

        trx = Transaction().add(
            TransactionInstruction(program_id=wrapper_program, data=data, keys=[
                AccountMeta(pubkey=token_program, is_signer=False, is_writable=False),
                AccountMeta(pubkey=source, is_signer=False, is_writable=True),
                AccountMeta(pubkey=destination, is_signer=False, is_writable=True),
                AccountMeta(pubkey=authority, is_signer=False, is_writable=False)])
        )

        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])
        


if __name__ == '__main__':
    unittest.main()
