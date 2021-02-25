from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
import unittest
import base58

from eth_tx_utils import make_keccak_instruction_data, make_instruction_data_from_tx
from solana_utils import *

class EvmLoaderTestsNewAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acc = RandomAccaunt()
        # cls.acc = RandomAccaunt('1613734358.json')
        # print(bytes(cls.acc.get_acc().public_key()).hex())
        if getBalance(cls.acc.get_acc().public_key()) == 0:
            print("request_airdrop for ", cls.acc.get_acc().public_key())
            cli = SolanaCli(solana_url, cls.acc)
            cli.call('airdrop 1000000')
            # tx = http_client.request_airdrop(cls.acc.get_acc().public_key(), 100000)
            # confirm_transaction(http_client, tx['result'])
            # balance = http_client.get_balance(cls.acc.get_acc().public_key())['result']['value']
            print("Done\n")
            
        cls.loader = EvmLoader(solana_url, cls.acc)
        # cls.loader = EvmLoader(solana_url, cls.acc, 'ChcwPA3VHaKHEuzikJXHEy6jP5Ycn9ZV7KYZXfeiNp5m')
        cls.evm_loader = cls.loader.loader_id
        # cls.owner_contract = cls.loader.deploy('evm_loader/hello_world.bin')
        # cls.owner_contract = "HAAfFJK4tsJb38LC2MULMzgpYkqAKRguyq7GRTocvGE9"

    def test_1(self):  
        tx_2 = "0xf86180808094535d33341d2ddcc6411701b1cf7634535f1e8d1680843917b3df26a013a4d8875dfc46a489c2641af798ec566d57852b94743b234517b73e239a5a22a07586d01a8a1125be7108ee6580c225a622c9baa0938f4d08abe78556c8674d58"
        (_, _, msg) =  make_instruction_data_from_tx(tx_2)
        trx = Transaction().add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("b1") + msg, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),             
            ]))
        tx = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, tx['result'])


    def test_2(self):  
        tx_2 = "0xf86180808094535d33341d2ddcc6411701b1cf7634535f1e8d1680843917b3df26a013a4d8875dfc46a489c2641af798ec566d57852b94743b234517b73e239a5a22a07586d01a8a1125be7108ee6580c225a622c9baa0938f4d08abe78556c8674d58"
        trx = Transaction().add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("b1") + bytearray.fromhex(tx_2[2:]), keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),             
            ]))
        tx = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, tx['result'])

    def test_3(self):  
        tx_2 = "0xf86180808094535d33341d2ddcc6411701b1cf7634535f1e8d1680843917b3df26a013a4d8875dfc46a489c2641af798ec566d57852b94743b234517b73e239a5a22a07586d01a8a1125be7108ee6580c225a622c9baa0938f4d08abe78556c8674d58"
        (_, _, msg) =  make_instruction_data_from_tx(tx_2)
        trx = Transaction().add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("b2") + msg, keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),             
            ]))
        tx = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, tx['result'])

    def test_4(self):  
        tx_2 = "0xf86180808094535d33341d2ddcc6411701b1cf7634535f1e8d1680843917b3df26a013a4d8875dfc46a489c2641af798ec566d57852b94743b234517b73e239a5a22a07586d01a8a1125be7108ee6580c225a622c9baa0938f4d08abe78556c8674d58"
        trx = Transaction().add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("b2") + bytearray.fromhex(tx_2[2:]), keys=[
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),             
            ]))
        tx = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, tx['result'])


if __name__ == '__main__':
    unittest.main()
