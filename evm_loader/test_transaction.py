from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
import unittest
import base58

from eth_tx_utils import make_random_request, make_request_w_params, make_instruction_data_from_tx, make_keccak_instruction_data
from solana_utils import *

class EvmLoaderTestsNewAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # cls.acc = RandomAccaunt()
        cls.acc = RandomAccaunt('1613736090.json')
        # print(bytes(cls.acc.get_acc().public_key()).hex())
        if getBalance(cls.acc.get_acc().public_key()) == 0:
            print("request_airdrop for ", cls.acc.get_acc().public_key())
            cli = SolanaCli(solana_url, cls.acc)
            cli.call('airdrop 1000000')
            # tx = http_client.request_airdrop(cls.acc.get_acc().public_key(), 100000)
            # confirm_transaction(http_client, tx['result'])
            # balance = http_client.get_balance(cls.acc.get_acc().public_key())['result']['value']
            print("Done\n")
            
        # cls.loader = EvmLoader(solana_url, cls.acc)
        cls.loader = EvmLoader(solana_url, cls.acc, 'Gj2YVsPRJkWnx9dv8bo9hcgBBQGCmticp2x5gKqQ35En')
        cls.evm_loader = cls.loader.loader_id
        # cls.owner_contract = cls.loader.deploy('evm_loader/hello_world.bin')
        cls.owner_contract = "CqjrFdRTR4Sw9tcqpaz2694XPd279D9er2oUEAsZCAGN"
        print("contract id: ", cls.owner_contract)
        print("contract id: ", solana2ether(cls.owner_contract).hex())

    def test_success_tx_send(self):
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        result = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, result['result'])

    def test_success_update_nonce(self):  
        (keccak_instruction, evm_instruction_data, from_addr, private) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        result = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, result['result'])

        (keccak_instruction_2, evm_instruction_data_2, _) = make_request_w_params(solana2ether(self.owner_contract), '3917b3df', 1, private)  

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction_2, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data_2, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        result = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, result['result'])      


    def test_fail_on_no_signature(self):  
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)
        
        trx = Transaction().add(
        TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
            AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
            AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
            AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
            AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
        ]))
        return http_client.send_transaction(trx, self.acc.get_acc())
            

    def test_fail_on_solana_signer(self):  
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        return http_client.send_transaction(trx, self.acc.get_acc())


    def test_fail_on_wrong_sender(self):  
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        def send_trx():
            trx = Transaction().add(
                TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                    AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
                ])).add(
                TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                    AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),
                    AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                    AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
                ]))
            return http_client.send_transaction(trx, self.acc.get_acc())

        err = "Sender must be Ethereum account. This method is not allowed for Solana accounts."
        with self.assertRaisesRegex(Exception, err):
            send_trx()


    def test_fail_on_wrong_nonce(self):  
        (_, _, _, private) = make_random_request(solana2ether(self.owner_contract), '3917b3df')   
        (keccak_instruction, evm_instruction_data, from_addr, private) = make_request_w_params(solana2ether(self.owner_contract), '3917b3df', 1, private)    

        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.get_acc().public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        return http_client.send_transaction(trx, self.acc.get_acc())


    def test_fail_on_transaction_w_same_nonce(self):  
        (keccak_instruction, evm_instruction_data, from_addr, private) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        result = http_client.send_transaction(trx, self.acc.get_acc())
        confirm_transaction(http_client, result['result'])

        (keccak_instruction, evm_instruction_data, from_addr) = make_request_w_params(solana2ether(self.owner_contract), '3917b3df', 0, private)  

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        http_client.send_transaction(trx, self.acc.get_acc())


    def test_check_wo_checks(self):  
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')        
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("05") + evm_instruction_data, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        http_client.send_transaction(trx, self.acc.get_acc())


    def test_raw_tx_wo_checks(self):  
        tx_2 = "0xf861808080947506f35ef3e06be897ee9a272aa956def5884f6b80843917b3df25a0ba769ca48fc9db6ae376e390081054afb550fc95c1a3b5a552947167e15224dea077280314eee8d604e628f0ed625c89df35bb4232a2f6ca8e6d5b57e483188a09"
        
        (from_addr, sign, msg) =  make_instruction_data_from_tx(tx_2)
        keccak_instruction = make_keccak_instruction_data(1, len(msg))                
        caller = create_ether_accaut(self.loader, from_addr)

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("05") + from_addr + sign + msg, keys=[
                AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),  
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),              
            ]))
        http_client.send_transaction(trx, self.acc.get_acc())


if __name__ == '__main__':
    unittest.main()
