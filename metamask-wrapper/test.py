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
user_private = [78,30,242,41,56,100,77,178,137,42,192,245,237,57,30,49,77,157,153,149,190,215,219,189,120,117,246,62,114,53,235,128,84,117,176,44,64,151,218,252,87,5,102,113,33,146,221,84,238,252,233,236,70,175,110,52,78,53,215,184,101,29,19,79]
user_public = '6ghLBF2LZAooDnmUMVm8tdNK6jhcAQhtbQiC7TgVnQ2r'
memo_program = 'BUAot6PmXs6nnnkik5hyR6atHhTcfu2WnCX2m6nKchG'
wrapper_program = 'C73XzAsmLjXZ7TA2naDytpqJ3h7UUm82AgSUoRS6vN3X'
#wrapper_program = 'HHEtqN8eMsKHtAX2W5Ndzu3cMJiTT2YXyBwzFYfPidn2'
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
    @classmethod
    def setUpClass(cls):
        version = http_client.get_version()['result']
        print(version)
        cls.acc = Account(b'\xdc~\x1c\xc0\x1a\x97\x80\xc2\xcd\xdfn\xdb\x05.\xf8\x90N\xde\xf5\x042\xe2\xd8\x10xO%/\xe7\x89\xc0<')
        print('Account:', cls.acc.public_key())
        print('Private:', cls.acc.secret_key())
        balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        if balance == 0:
            tx = http_client.request_airdrop(cls.acc.public_key(), 10*10**9)
            confirm_transaction(http_client, tx['result'])
            balance = http_client.get_balance(cls.acc.public_key())['result']['value']
        print('Balance:', balance)

    def test_account(self):
        print(self.acc.public_key())
        print(http_client.get_account_info(self.acc.public_key()))

    def test_send_memo(self):
        keys = [
            AccountMeta(pubkey = self.acc.public_key(), is_signer=True, is_writable=False)
        ]
        keys2 = [
            AccountMeta(pubkey = user_public, is_signer=False, is_writable=False)
        ]
        data = bytes([0xff])
        trx = Transaction().add(
            TransactionInstruction(keys=keys, program_id=memo_program, data=data))
        result = http_client.send_transaction(trx, self.acc)
        self.assertTrue('error' in result)
        data = 'Hello world'.encode('utf8')
        trx = Transaction().add(
            TransactionInstruction(keys=keys, program_id=memo_program, data=data),
            TransactionInstruction(keys=keys2, program_id=memo_program, data=bytes([0x0])))
        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])
        print("Confirmed")

    def test_init_metamask_token(self):
        keys = [
            AccountMeta(pubkey = self.acc.public_key(), is_signer=False, is_writable=True)
        ]
        base = self.acc.public_key()
        seed = '1'*32
        owner = PublicKey(wrapper_program)
        account = PublicKey(hashlib.sha256(bytes(base) + seed.encode('utf8') + bytes(owner)).digest())
#        _account = Account()
#        account = _account.public_key()
        mint = PublicKey(memo_program)
        print('Base:', base)
        print('Seed:', seed)
        print('Owner:', owner)
        print('Account:', account)
        print('Mint:', mint, bytes(mint).hex())
        allocateData = ALLOCATE_WITH_SEED_LAYOUT.build(dict(
            instruction=9,
            base=bytes(base),
            seed=dict(length=len(seed),chars=seed),
            space=33,
            owner=bytes(owner)))
#        allocateData = CREATE_ACCOUNT_LAYOUT.build(dict(
#            instruction=0,
#            lamports=10**6,
#            space=33,
#            owner=bytes(owner)))
        initializeData = INITIALIZE_TOKEN_LAYOUT.build(dict(
            instruction=0, # Initialize
            program=bytes(mint),
            token=bytes(mint)))
        print("Allocate data:", allocateData.hex())
        print("Initialize data:", initializeData.hex())
        trx = Transaction().add(
            TransactionInstruction(program_id=system_id, data=allocateData, keys=[
                AccountMeta(pubkey=account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=base, is_signer=True, is_writable=True),
#                AccountMeta(pubkey=account, is_signer=True, is_writable=True),
            ])
        ).add(
            TransactionInstruction(program_id=wrapper_program, data=initializeData, keys=[
                AccountMeta(pubkey=str(account), is_signer=False, is_writable=True),
                AccountMeta(pubkey=str(mint), is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
            ])
        )
        print(self.acc)
        result = http_client.send_transaction(trx, self.acc)
        print('Send transaction result:', result)
        self.assertTrue('result' in result)
        confirm_transaction(http_client, result['result'])

    def test_create_with_seed(self):
        base = base58.b58decode('6ghLBF2LZAooDnmUMVm8tdNK6jhcAQhtbQiC7TgVnQ2r')
        seed = bytes('1', 'utf8')
        owner = base58.b58decode('C73XzAsmLjXZ7TA2naDytpqJ3h7UUm82AgSUoRS6vN3X')
        acc = hashlib.sha256(base+seed+owner).digest()
        print(base58.b58encode(acc))

    def test_get_program_accounts(self):
        print('Wrapper_program:', wrapper_program)
        res = http_client.get_program_accounts(self.acc.public_key())
        print(json.dumps(res, indent=3))

if __name__ == '__main__':
    unittest.main()
