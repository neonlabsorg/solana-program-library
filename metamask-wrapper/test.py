# TO run this test, use default solana's ./run.sh, but to spl-genesis-args.sh add:
# --bpf-program MetamaskW1111111111111111111111111111111111 BPFLoader1111111111111111111111111111111111 metamask-wrapper.so 

import time
import unittest
import json
from solana.rpc.api import Client
from solana.account import Account
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
from solana._layouts.shared import PUBLIC_KEY_LAYOUT, RUST_STRING_LAYOUT
from solana.sysvar import SYSVAR_RENT_PUBKEY
from nacl import public
import base58
import hashlib
from construct import Int8ul, Int32ul, Int64ul, Pass  # type: ignore
from construct import Struct as cStruct

http_client = Client("http://localhost:8899")
memo_program = 'Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo'
token_program = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
metamask_program = 'MetamaskW1111111111111111111111111111111111'
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
    "token" / PUBLIC_KEY_LAYOUT,
    "program" / PUBLIC_KEY_LAYOUT,
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
            break
        elapsed_time += sleep_time
    if not resp["result"]:
        raise RuntimeError("could not confirm transaction: ", tx_sig)
    return resp

class SolanaTests(unittest.TestCase):
    version_recommended = '1.3.9'

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
        cls.checkProgramInstalled(memo_program)
        cls.checkProgramInstalled(token_program)
        cls.checkProgramInstalled(metamask_program)

        cls.acc = Account(b'\xdc~\x1c\xc0\x1a\x97\x80\xc2\xcd\xdfn\xdb\x05.\xf8\x90N\xde\xf5\x042\xe2\xd8\x10xO%/\xe7\x89\xc0<')
        print('Account:', cls.acc.public_key())
        print('Private:', cls.acc.secret_key())
        balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        if balance == 0:
            tx = http_client.request_airdrop(cls.acc.public_key(), 10*10**9)
            confirm_transaction(http_client, tx['result'])
            balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        print('Balance:', balance)

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

    def test_send_memo(self):
        keys = [
            AccountMeta(pubkey = self.acc.public_key(), is_signer=True, is_writable=False)
        ]
        mint = PublicKey(memo_program)
        initializeData = INITIALIZE_TOKEN_LAYOUT.build(dict(
            instruction=2, # Initialize
            program=bytes(mint),
            token=bytes(mint)))
        trx = Transaction().add(
            TransactionInstruction(keys=keys, program_id=token_program, data=initializeData))
        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])
        print("Confirmed")

if __name__ == '__main__':
    unittest.main()
