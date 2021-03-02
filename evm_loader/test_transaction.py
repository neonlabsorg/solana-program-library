from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
import unittest

from eth_tx_utils import make_random_request, make_request_w_params
from solana_utils import *


class EvmLoaderTestsNewAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acc = RandomAccaunt()
        # cls.acc = RandomAccaunt('1614333419.json')
        # print(bytes(cls.acc.get_acc().public_key()).hex())
        if getBalance(cls.acc.get_acc().public_key()) == 0:
            print("request_airdrop for ", cls.acc.get_acc().public_key())
            cli = SolanaCli(solana_url, cls.acc)
            cli.call('airdrop 1000000')
            # balance = http_client.get_balance(cls.acc.get_acc().public_key())['result']['value']
            print("Done\n")

        cls.loader = EvmLoader(solana_url, cls.acc)
        # cls.loader = EvmLoader(solana_url, cls.acc, 'HyQzZ3H1spUQiDekgu5e3R1Xhg1HuhEFZGRtgM6gGLto')
        cls.evm_loader = cls.loader.loader_id
        cls.owner_contract = cls.loader.deploy('evm_loader/hello_world.bin')
        # cls.owner_contract = "6LZ1sMJZQkvDD4ukadT8AU6XEmCQvTEuR5bCeGwT9c4x"
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
        http_client.send_transaction(trx, self.acc.get_acc())

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

    def test_fail_on_no_signature(self):
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')
        caller = create_ether_accaut(self.loader, from_addr)

        def send_trx():
            trx = Transaction().add(
                TransactionInstruction(program_id=self.evm_loader, data=bytearray.fromhex("a1") + evm_instruction_data, keys=[
                    AccountMeta(pubkey=self.owner_contract, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=caller, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),
                    AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),
                ]))
            return http_client.send_transaction(trx, self.acc.get_acc())

        err = "missing required signature for instruction"
        with self.assertRaisesRegex(Exception, err):
            send_trx()

    def test_fail_on_solana_signer(self):
        (keccak_instruction, evm_instruction_data, from_addr, _) = make_random_request(solana2ether(self.owner_contract), '3917b3df')
        caller = create_ether_accaut(self.loader, from_addr)

        def send_trx():
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

        err = "Error processing Instruction"
        with self.assertRaisesRegex(Exception, err):
            send_trx()

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

        err = "invalid account data for instruction"
        with self.assertRaisesRegex(Exception, err):
            send_trx()

    def test_fail_on_wrong_nonce(self):
        (_, _, _, private) = make_random_request(solana2ether(self.owner_contract), '3917b3df')
        (keccak_instruction, evm_instruction_data, from_addr) = make_request_w_params(solana2ether(self.owner_contract), '3917b3df', 1, private)

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

        err = "invalid account data for instruction"
        with self.assertRaisesRegex(Exception, err):
            send_trx()

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

        def send_trx():
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
            return http_client.send_transaction(trx, self.acc.get_acc())

        err = "invalid program argument"
        with self.assertRaisesRegex(Exception, err):
            send_trx()

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


if __name__ == '__main__':
    unittest.main()
