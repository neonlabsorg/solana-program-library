import unittest
from base58 import b58decode
from solana_utils import *
from eth_tx_utils import make_keccak_instruction_data, make_instruction_data_from_tx, Trx
from eth_utils import abi
from web3.auto import w3
from eth_keys import keys
from web3 import Web3


solana_url = os.environ.get("SOLANA_URL", "http://localhost:8899")
http_client = Client(solana_url)
# CONTRACTS_DIR = os.environ.get("CONTRACTS_DIR", "evm_loader/")
CONTRACTS_DIR = os.environ.get("CONTRACTS_DIR", "")
# evm_loader_id = os.environ.get("EVM_LOADER")
evm_loader_id = "7LyT3W3pjh262XwivY79hxQVebVb1CXPNh5NMdN2FjPL"

sysinstruct = "Sysvar1nstructions1111111111111111111111111"
keccakprog = "KeccakSecp256k11111111111111111111111111111"
sysvarclock = "SysvarC1ock11111111111111111111111111111111"


def emulator(contract, sender, data):
    cmd = 'neon-cli --evm_loader {} --url {} emulate {} {} {}'.format(evm_loader_id, solana_url, contract, sender, data)
    print (cmd)
    try:
        return subprocess.check_output(cmd, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        import sys
        print("ERR: solana error {}".format(err))
        raise


def call_emulated(contract_id, caller_id, data):
    output = emulator(contract_id, caller_id, data)
    result = json.loads(output)
    print("call_emulated %s %s %s return %s", contract_id, caller_id, data, result)
    exit_status = result['exit_status']
    if exit_status == 'revert':
        offset = int(result['result'][8:8 + 64], 16)
        length = int(result['result'][8 + 64:8 + 64 + 64], 16)
        message = str(bytes.fromhex(result['result'][8 + offset * 2 + 64:8 + offset * 2 + 64 + length * 2]), 'utf8')
        raise Exception("execution reverted:", message , "data:", '0x', "result:", result['result'])
    if result["exit_status"] != "succeed":
        raise Exception("evm emulator error ", result)
    return result


class EventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wallet = WalletAccount(wallet_path())
        cls.loader = EvmLoader(solana_url, wallet, evm_loader_id)
        cls.acc = wallet.get_acc()

        # Create ethereum account for user account
        cls.caller_ether = eth_keys.PrivateKey(cls.acc.secret_key()).public_key.to_canonical_address()
        (cls.caller, cls.caller_nonce) = cls.loader.ether2program(cls.caller_ether)

        if getBalance(cls.caller) == 0:
            print("Create caller account...")
            _ = cls.loader.createEtherAccount(cls.caller_ether)
            print("Done\n")

        print('Account:', cls.acc.public_key(), bytes(cls.acc.public_key()).hex())
        print("Caller:", cls.caller_ether.hex(), cls.caller_nonce, "->", cls.caller,
              "({})".format(bytes(PublicKey(cls.caller)).hex()))

        (cls.reId_contract, cls.reId_contract_eth, cls.reId_contract_code) = cls.loader.deployChecked(CONTRACTS_DIR+"helloWorld.binary", solana2ether(cls.acc.public_key()))
        print ('reId_contract', cls.reId_contract)
        print ('reId_contract_eth', cls.reId_contract_eth.hex())
        print ('reId_contract_code', cls.reId_contract_code)

    def sol_instr_keccak(self, keccak_instruction):
        return TransactionInstruction(program_id=keccakprog, data=keccak_instruction, keys=[
            AccountMeta(pubkey=PublicKey(keccakprog), is_signer=False, is_writable=False), ])

    def sol_instr_09_partial_call(self, storage_account, step_count, evm_instruction):
        return TransactionInstruction(program_id=self.loader.loader_id,
                                   data=bytearray.fromhex("09") + step_count.to_bytes(8, byteorder='little') + evm_instruction,
                                   keys=[
                                       AccountMeta(pubkey=storage_account, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.reId_contract, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.reId_contract_code, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=PublicKey(sysinstruct), is_signer=False, is_writable=False),
                                       AccountMeta(pubkey=self.loader.loader_id, is_signer=False, is_writable=False),
                                       AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
                                   ])

    def sol_instr_10_continue(self, storage_account, step_count, evm_instruction):
        return TransactionInstruction(program_id=self.loader.loader_id,
                                   data=bytearray.fromhex("0A") + step_count.to_bytes(8, byteorder='little') + evm_instruction,
                                   keys=[
                                       AccountMeta(pubkey=storage_account, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.reId_contract, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.reId_contract_code, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                                       AccountMeta(pubkey=PublicKey(sysinstruct), is_signer=False, is_writable=False),
                                       AccountMeta(pubkey=self.loader.loader_id, is_signer=False, is_writable=False),
                                       AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
                                   ])
    def create_storage_account(self, seed):
        storage = PublicKey(sha256(bytes(self.acc.public_key()) + bytes(seed, 'utf8') + bytes(PublicKey(self.loader.loader_id))).digest())
        print("Storage", storage)

        if getBalance(storage) == 0:
            trx = Transaction()
            trx.add(createAccountWithSeed(self.acc.public_key(), self.acc.public_key(), seed, 10**9, 128*1024, PublicKey(evm_loader_id)))
            http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=False))

        return storage

    def call_partial_signed(self, input):
        print("solana2ether(self.reId_contract)", solana2ether(self.reId_contract))
        tx = {'to': self.reId_contract_eth, 'value': 1, 'gas': 1, 'gasPrice': 1,
            'nonce': getTransactionCount(http_client, self.caller), 'data': input, 'chainId': 111}

        signed_tx = w3.eth.account.sign_transaction(tx, self.acc.secret_key())
        # print(signed_tx.rawTransaction.hex())
        _trx = Trx.fromString(signed_tx.rawTransaction)

        output_json = call_emulated(_trx.toAddress.hex(), self.caller_ether.hex(), _trx.callData.hex())
        print("emulator returns: %s", json.dumps(output_json, indent=3))

        (from_addr, sign, msg) = make_instruction_data_from_tx(tx, self.acc.secret_key())
        assert (from_addr == self.caller_ether)
        instruction = from_addr + sign + msg

        storage = self.create_storage_account(sign[:8].hex())

        trx = Transaction()
        trx.add(self.sol_instr_keccak(make_keccak_instruction_data(1, len(msg), 9)))
        trx.add(self.sol_instr_09_partial_call(storage, 100, instruction))
        http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=False, preflight_commitment="root"))["result"]

        while (True):
            print("Continue")
            trx = Transaction()
            trx.add(self.sol_instr_10_continue(storage, 100, instruction))
            result = http_client.send_transaction(trx, self.acc, opts=TxOpts(skip_confirmation=False, preflight_commitment="root"))["result"]

            if (result['meta']['innerInstructions'] and result['meta']['innerInstructions'][0]['instructions']):
                data = b58decode(result['meta']['innerInstructions'][0]['instructions'][-1]['data'])
                if (data[0] == 6):
                    return result


    def test_callHelloWorld(self):

        func_name = abi.function_signature_to_4byte_selector('callHelloWorld()')
        data = (func_name)
        result = self.call_partial_signed(input=data)
        print (result)
