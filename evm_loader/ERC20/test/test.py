from solana.rpc.api import Client
from solana.account import Account
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
from solana.sysvar import *
import unittest
import time
import os
import json
import base58
import subprocess
import unittest
from eth_tx_utils import make_keccak_instruction_data, make_instruction_data_from_tx

tokenkeg = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
sysvarclock = "SysvarC1ock11111111111111111111111111111111"
solana_url = os.environ.get("SOLANA_URL", "http://localhost:8899")
http_client = Client(solana_url)
# evm_loader = os.environ.get("EVM_LOADER")
evm_loader = "5rpSFgyx4mAJQpPffvggvKodsGzf1kkus28SkXAnsUZF"
path_to_evm_loader = '../../../target/bpfel-unknown-unknown/release/evm_loader.so'

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
    def __init__(self, url):
        self.url = url

    def call(self, arguments):
        cmd = 'solana --url {} {}'.format(self.url, arguments)
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            import sys
            print("ERR: solana error {}".format(err))
            raise

class SplToken:
    def __init__(self, url):
        self.url = url

    def call(self, arguments):
        cmd = 'spl-token --url {} {}'.format(self.url, arguments)
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            import sys
            print("ERR: spl-token error {}".format(err))
            raise

class EvmLoader:
    loader_id = evm_loader

    def __init__(self, solana_url, loader_id=None):
        if not loader_id and not EvmLoader.loader_id:
            print("Load EVM loader...")
            cli = SolanaCli(solana_url)
            contract = path_to_evm_loader
            result = json.loads(cli.call('deploy {}'.format(contract)))
            programId = result['programId']
            EvmLoader.loader_id = programId
            print("Done\n")

        self.solana_url = solana_url
        self.loader_id = loader_id or EvmLoader.loader_id
        print("Evm loader program: {}".format(self.loader_id))

    def deploy(self, contract):
        cli = SolanaCli(self.solana_url)
        output = cli.call("deploy --use-evm-loader {} {}".format(self.loader_id, contract))
        print(type(output), output)
        return json.loads(output.splitlines()[-1])

    def createEtherAccount(self, ether):
        cli = SolanaCli(self.solana_url)
        output = cli.call("create-ether-account {} {} 1".format(self.loader_id, ether.hex()))
        result = json.loads(output.splitlines()[-1])
        return result["solana"]

    def ether2program(self, ether):
        cli = SolanaCli(self.solana_url)
        output = cli.call("create-program-address {} {}".format(ether.hex(), self.loader_id))
        items = output.rstrip().split('  ')
        return (items[0], int(items[1]))

    def deployERC20(self, location_hex, location_bin,  mintId, balance_erc20):
        ctor_init = str("%064x" % 0xa0) + \
                    str("%064x" % 0xe0) + \
                    str("%064x" % 0x9) + \
                    base58.b58decode(balance_erc20).hex() + \
                    base58.b58decode(mintId).hex() + \
                    str("%064x" % 0x1) + \
                    str("77%062x" % 0x00) + \
                    str("%064x" % 0x1) + \
                    str("77%062x" % 0x00)

        with open(location_hex, mode='r') as hex:
            binary = bytearray.fromhex(hex.read() + ctor_init)
            with open(location_bin, mode='wb') as bin:
                bin.write(binary)
                return self.deploy(location_bin)

def solana2ether(public_key):
    from web3 import Web3
    return bytes(Web3.keccak(bytes(PublicKey(public_key)))[-20:])


def getBalance(account):
    return http_client.get_balance(account)['result']['value']


class EvmLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = EvmLoader(solana_url, evm_loader)

        # Initialize user account
        cli = SolanaCli(solana_url)
        res = cli.call("config get")
        res = res.splitlines()[-1]
        substr = "Keypair Path: "
        if not res.startswith(substr):
            raise Exception("cannot get keypair path")
        path = res[len(substr):]
        with open(path.strip(), mode='r') as file:
            pk = (file.read())
            nums = list(map(int, pk.strip("[]").split(',')))
            nums = nums[0:32]
            values = bytes(nums)
            cls.acc = Account(values)

        # Create ethereum account for user account
        cls.caller_ether = bytes.fromhex("cf9f430be7e6c473ec1556004650328c71051bd4")
        # cls.caller_ether = solana2ether(cls.acc.public_key())
        (cls.caller, cls.caller_nonce) = cls.loader.ether2program(cls.caller_ether)

        info = http_client.get_account_info(cls.caller)
        if info['result']['value'] is None:
            print("Create caller account...")
            cls.caller = cls.loader.createEtherAccount(cls.caller_ether)
            print("Done")
            print("cls.caller:", cls.caller)

        if getBalance(cls.acc.public_key()) == 0:
            print("Create user account...")
            tx = http_client.request_airdrop(cls.acc.public_key(), 10*10**9)
            confirm_transaction(http_client, tx['result'])
            # balance = http_client.get_balance(cls.acc.public_key())['result']['value']
            print("Done\n")

        print('Account:', cls.acc.public_key(), bytes(cls.acc.public_key()).hex())
        print("Caller:", cls.caller_ether.hex(), cls.caller_nonce, "->", cls.caller, "({})".format(bytes(PublicKey(cls.caller)).hex()))

    def createMint(self):
        spl = SplToken(solana_url)
        res = spl.call("create-token")
        if not res.startswith("Creating token "):
            raise Exception("create token error")
        else:
            return res[15:59]

    def createTokenAccount(self, mint_id):
        spl = SplToken(solana_url)
        res = spl.call("create-account {}".format(mint_id))
        if not res.startswith("Creating account "):
            raise Exception("create account error")
        else:
            return res[17:61]

    def changeOwner(self, acc, owner):
        spl = SplToken(solana_url)
        res = spl.call("authorize {} owner {}".format(acc, owner))
        pos = res.find("New owner: ")
        if owner != res[pos+11:pos+55]:
            raise Exception("change owner error")

    def tokenMint(self, mint_id, recipient, amount):
        spl = SplToken(solana_url)
        res = spl.call("mint {} {} {}".format(mint_id, amount, recipient))
        print ("minting {} tokens for {}".format(amount, recipient))

    def tokenBalance(self, acc):
        spl = SplToken(solana_url)
        return int(spl.call("balance {}".format(acc)).rstrip())

    def erc20_deposit(self, payer, amount, erc20, balance_erc20, mint_id, evm_loader_id):
        # input = bytearray.fromhex(
        #     "036f0372af" +
        #     base58.b58decode(payer).hex() +
        #     str("%024x" % 0) + self.caller_ether.hex() +
        #     self.acc.public_key()._key.hex() +
        #     "%064x" % amount
        # )
        # trx = Transaction().add(
        #     TransactionInstruction(program_id=evm_loader_id, data=input, keys=
        #     [
        #         AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
        #         AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
        #         # AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
        #         AccountMeta(pubkey=payer, is_signer=False, is_writable=True),
        #         AccountMeta(pubkey=balance_erc20, is_signer=False, is_writable=True),
        #         AccountMeta(pubkey=mint_id, is_signer=False, is_writable=False),
        #         AccountMeta(pubkey=tokenkeg, is_signer=False, is_writable=False),
        #         # AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
        #         AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
        #     ]))
        # result = http_client.send_transaction(trx, self.acc)
        # result = confirm_transaction(http_client, result["result"])
        # messages = result["result"]["meta"]["logMessages"]
        # res = messages[messages.index("Program log: succeed") + 1]
        # if not res.startswith("Program log: "):
        #     raise Exception("Invalid program logs: no result")
        # else:
        #     print("deposit {}".format(int(res[13:], 16)))

        input = "6f0372af" + \
            base58.b58decode(payer).hex() + \
            str("%024x" % 0) + self.caller_ether.hex() + \
            self.acc.public_key()._key.hex() + \
            "%064x" % amount

        tx_1 = {
            'to': solana2ether(erc20),
            'value': 0,
            'gas': 0,
            'gasPrice': 0,
            'nonce': 0,
            'data': input,
            'chainId': 1
        }

        (from_addr, sign, msg) = make_instruction_data_from_tx(tx_1, self.acc.secret_key())
        keccak_instruction = make_keccak_instruction_data(1, len(msg))

        (caller, caller_nonce) = self.loader.ether2program(from_addr)
        print(" ether: " + from_addr.hex())
        print("solana: " + caller)
        print(" nonce: " + str(caller_nonce))

        if getBalance(caller) == 0:
            print("Create caller account...")
            caller_created = self.loader.createEtherAccount(from_addr)
            print("Done\n")

        # (from_addr, sign, msg) = make_instruction_data_from_tx(tx_1, self.acc.secret_key())
        # keccak_instruction = make_keccak_instruction_data(1, len(msg))

        trx = Transaction().add(
            TransactionInstruction(program_id="KeccakSecp256k11111111111111111111111111111", data=keccak_instruction, keys=[
                AccountMeta(pubkey=PublicKey("KeccakSecp256k11111111111111111111111111111"), is_signer=False, is_writable=False),
            ])).add(
            TransactionInstruction(program_id=evm_loader_id, data=bytearray.fromhex("a1") + from_addr + sign + msg, keys=[
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=caller, is_signer=False, is_writable=True),

                # AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                # AccountMeta(pubkAney=payer, is_signer=False, is_writable=True),
                AccountMeta(pubkey=balance_erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=mint_id, is_signer=False, is_writable=False),
                # AccountMeta(pubkey=tokenkeg, is_signer=False, is_writable=False),

                AccountMeta(pubkey=PublicKey("Sysvar1nstructions1111111111111111111111111"), is_signer=False, is_writable=False),
                AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),
            ]))

        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            print("deposit {}".format(int(res[13:], 16)))

    def erc20_withdraw(self, receiver, amount, erc20, balance_erc20, mint_id, evm_loader_id):
        input = bytearray.fromhex(
            "03441a3e70" +
            base58.b58decode(receiver).hex() +
            "%064x" % amount
        )
        trx = Transaction().add(
            TransactionInstruction(program_id=evm_loader_id, data=input, keys=
            [
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                # signer
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                # from
                AccountMeta(pubkey=balance_erc20, is_signer=False, is_writable=True),
                # to
                AccountMeta(pubkey=receiver, is_signer=False, is_writable=True),
                # mint_id
                AccountMeta(pubkey=mint_id, is_signer=False, is_writable=False),
                AccountMeta(pubkey=tokenkeg, is_signer=False, is_writable=False),
                AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False,  is_writable=False),
            ]))
        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            print("withdraw {}".format(int(res[13:], 16)))



    def erc20_balance(self, erc20, evm_loader_id):
        input = bytearray.fromhex(
            "0370a08231" +
            str("%024x" % 0) + self.caller_ether.hex()
        )
        trx = Transaction().add(
            TransactionInstruction(program_id=evm_loader_id, data=input, keys=
            [
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
            ]))

        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            return int(res[13:], 16)


    def erc20_transfer(self, erc20, evm_loader_id, eth_to, amount):
        input = bytearray.fromhex(
            "03a9059cbb" +
            str("%024x" % 0) + eth_to +
            "%064x" % amount
        )
        trx = Transaction().add(
            TransactionInstruction(program_id=evm_loader_id, data=input, keys=
            [
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
            ]))

        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        print("erc20 transfer signature: {}".format(result["result"]["transaction"]["signatures"][0]))
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            print("erc20 transfer {} ".format(res[13:]))


    def erc20_balance_ext(self, erc20, evm_loader_id):
        input = bytearray.fromhex("0340b6674d")
        trx = Transaction().add(
            TransactionInstruction(program_id=evm_loader_id, data=input, keys=
            [
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
            ]))

        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            return res[13:]

    def erc20_mint_id(self, erc20, evm_loader_id):
        input = bytearray.fromhex("03e132a122")
        trx = Transaction().add(
            TransactionInstruction(program_id=evm_loader_id, data=input, keys=
            [
                AccountMeta(pubkey=erc20, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.caller, is_signer=False, is_writable=True),
                AccountMeta(pubkey=self.acc.public_key(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=PublicKey(sysvarclock), is_signer=False, is_writable=False),
            ]))

        result = http_client.send_transaction(trx, self.acc)
        result = confirm_transaction(http_client, result["result"])
        messages = result["result"]["meta"]["logMessages"]
        res = messages[messages.index("Program log: succeed") + 1]
        if not res.startswith("Program log: "):
            raise Exception("Invalid program logs: no result")
        else:
            return res[13:]


    def test_erc20(self):
        mintId = self.createMint()
        time.sleep(20)
        print("\ncreate token:", mintId)
        acc_client = self.createTokenAccount(mintId)
        print ("create account acc_client:", acc_client)
        balance_erc20 = self.createTokenAccount(mintId)
        print ("create account balance_erc20:", balance_erc20)

        deploy_result= self.loader.deployERC20("erc20_ctor_uninit.hex", "erc20.bin",  mintId, balance_erc20)
        erc20Id = deploy_result["programId"]
        erc20Id_ether = bytearray.fromhex(deploy_result["ethereum"][2:])

        print ("erc20_id:", erc20Id)
        print ("erc20_id_ethereum:", erc20Id_ether.hex())
        time.sleep(20)
        print("erc20 balance_ext():", self.erc20_balance_ext( erc20Id, self.loader.loader_id))
        print("erc20 mint_id():", self.erc20_mint_id( erc20Id, self.loader.loader_id))

        self.changeOwner(balance_erc20, erc20Id)
        print("balance_erc20 owner changed to {}".format(erc20Id))
        mint_amount = 100
        self.tokenMint(mintId, acc_client, mint_amount)
        time.sleep(20)
        assert(self.tokenBalance(acc_client) == mint_amount)
        assert(self.tokenBalance(balance_erc20) == 0)
        assert(self.erc20_balance( erc20Id, self.loader.loader_id) == 0)

        deposit_amount = 1
        self.erc20_deposit( acc_client,  deposit_amount*(10**9), erc20Id, balance_erc20, mintId, self.loader.loader_id)
        assert(self.tokenBalance(acc_client) == mint_amount-deposit_amount)
        assert(self.tokenBalance(balance_erc20) == deposit_amount)
        assert(self.erc20_balance( erc20Id, self.loader.loader_id) == deposit_amount*(10**9))
        self.erc20_withdraw( acc_client, deposit_amount*(10**9), erc20Id, balance_erc20, mintId, self.loader.loader_id)
        assert(self.tokenBalance(acc_client) == mint_amount)
        assert(self.tokenBalance(balance_erc20) == 0)
        assert(self.erc20_balance( erc20Id, self.loader.loader_id) == 0)


    # @unittest.skip("not for CI")
    def test_dep(self):
        print("test_dep")
        acc_client = "Fda8oxqwnch7soumCXPPyTckbLVQ1FckuE1B5c6pV82r"
        erc20Id = "EHoMc1NwjuBnDcjhczpQgiQ268kL4mbUT7hkiNszMVRZ"
        balance_erc20= "1nqiH9YUkU3FAACb1eYKQjA9r1mGKkKW3veCFJ3gyug"
        mintId = "D4fcZmhhgcKuj9xZVcFCY99WiLxBPNxNBbuM4yNRTdM6"
        self.erc20_deposit( acc_client,  50, erc20Id, balance_erc20, mintId, self.loader.loader_id)

    def test_with_draw(self):
        print("test_dep")
        acc_client = "Fda8oxqwnch7soumCXPPyTckbLVQ1FckuE1B5c6pV82r"
        erc20Id = "sr9JLRv6U9vYcm6PHDSyREfUwqw8dzKBz4CTqFcBq4B"
        balance_erc20= "HjpNJwDPApLjrDuFagw8HkQwQrgF5B6Ps9cjdGqcpvGC"
        mintId = "D4fcZmhhgcKuj9xZVcFCY99WiLxBPNxNBbuM4yNRTdM6"
        self.erc20_withdraw(acc_client,  10, erc20Id, balance_erc20, mintId, self.loader.loader_id)

    @unittest.skip("not for CI")
    def test_balance_ext(self):
        print("test_balance_ext")
        erc20Id = "EHoMc1NwjuBnDcjhczpQgiQ268kL4mbUT7hkiNszMVRZ"
        print(self.erc20_balance_ext( erc20Id, self.loader.loader_id))

    @unittest.skip("not for CI")
    def test_mint_id(self):
        print("test_mint_id")
        erc20Id = "7G3Pihd5ZMtCD91N2vc2hEmwt1yC4Sbk2eDtAGyTG9NV"
        self.erc20_mint_id( erc20Id, self.loader.loader_id)

    # @unittest.skip("not for CI")
    def test_balance(self):
        print("test_balance")
        erc20Id = "EHoMc1NwjuBnDcjhczpQgiQ268kL4mbUT7hkiNszMVRZ"
        print(self.erc20_balance( erc20Id, self.loader.loader_id, ))

    @unittest.skip("not for CI")
    def test_tranfer(self):
        print("test_transfer")
        erc20Id = "7G3Pihd5ZMtCD91N2vc2hEmwt1yC4Sbk2eDtAGyTG9NV"
        self.erc20_transfer( erc20Id, self.loader.loader_id, "0000000000000000000000000000000000000011", 1)


if __name__ == '__main__':
    unittest.main()

