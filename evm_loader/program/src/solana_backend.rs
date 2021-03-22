use evm::{
    backend::{Basic, Backend, Apply},
    CreateScheme, Capture, Transfer, ExitReason
};
use core::convert::Infallible;
use primitive_types::{H160, H256, U256};
use sha3::{Digest, Keccak256};
use solana_sdk::{
    account::Account,
    account_info::AccountInfo,
    pubkey::Pubkey,
    instruction::{Instruction, AccountMeta},
    program::invoke_signed,
};
use std::{
    cell::RefCell,
    convert::TryInto,
    collections::{HashMap, HashSet},
};
use serde::{Deserialize, Serialize};

use crate::solidity_account::SolidityAccount;
use solana_sdk::program_error::ProgramError;
// use crate::constatns::ProgramError;

fn keccak256_digest(data: &[u8]) -> H256 {
    H256::from_slice(Keccak256::digest(&data).as_slice())
}

pub fn solidity_address<'a>(key: &Pubkey) -> H160 {
    H256::from_slice(key.as_ref()).into()
}

fn u256_to_h256(value: U256) -> H256 {
    let mut v = vec![0u8; 32];
    value.to_big_endian(&mut v);
    H256::from_slice(&v)
}

#[derive(Serialize, Deserialize, Debug)]
struct AccountJSON {
    address: String,
    writable: bool,
    new: bool,
}

pub struct SolanaBackend<'a> {    
    accounts: RefCell<HashMap<H160, SolidityAccount<'a>>>,
    account_infos: Option<&'a [AccountInfo<'a>]>,

    get_account: Option<&'a dyn Fn(&Pubkey) -> Option<Account>>,
    base_account: Option<Pubkey>,
    new_accounts: RefCell<HashSet<H160>>,

    program_id: Pubkey,
    contract_id: H160,
    caller_id: H160,

    block_number: U256,
    block_timestamp: U256,
}

impl<'a> SolanaBackend<'a> {
    pub fn new(program_id: &Pubkey, account_infos: &'a [AccountInfo<'a>], slot: u64, timestamp: i64) -> Result<Self,ProgramError> {
        debug_print!("backend::new");
        let mut accounts = HashMap::new();

        let mut contract_id = H160::from_slice(&[0xffu8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8]);
        let mut caller_id = H160::from_slice(&[0xffu8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8]);

        for (i, account) in (&account_infos).iter().enumerate() {
            if account.owner == program_id {
                let sol_account = SolidityAccount::new(account.key.clone(), account.data.clone(), (*account.lamports.borrow()).clone())?;
                if i == 0 {
                    contract_id = sol_account.account_data.ether;
                } else if i == 1 {
                    caller_id = sol_account.account_data.ether;
                }
                accounts.insert(sol_account.account_data.ether, sol_account);
            }
        };
        debug_print!("Accounts was read");

        Ok(Self {
            accounts: RefCell::new(accounts),
            account_infos: Some(account_infos),

            new_accounts: RefCell::new(HashSet::new()),    
            get_account: None,        
            base_account: None,

            program_id: program_id.clone(),        
            contract_id: contract_id,
            caller_id: caller_id,
        
            block_number: slot.into(),
            block_timestamp: timestamp.into(),
        })
    }

    pub fn new_emulator(base_account: Pubkey, program_id: Pubkey, contract_id: H160, caller_id: H160, slot: u64, timestamp: i64, get_account: &'a dyn Fn(&Pubkey) -> Option<Account>) -> Result<Self, u8> {
        eprintln!("backend::new");

        Ok(Self {            
            accounts: RefCell::new(HashMap::new()),
            account_infos: None,

            new_accounts: RefCell::new(HashSet::new()),       
            get_account: Some(get_account),        
            base_account: Some(base_account),

            program_id: program_id,        
            contract_id: contract_id,
            caller_id: caller_id,
        
            block_number: slot.into(),
            block_timestamp: timestamp.into(),
        })
    }

    fn create_acc_if_not_exists(&self, address: H160) {
        if self.get_account.is_none() {
            return;
        }

        let mut accounts = self.accounts.borrow_mut(); 
        let mut new_accounts = self.new_accounts.borrow_mut();

        if accounts.get(&address).is_none() {
            //let (solana_address, _) = Pubkey::find_program_address(&[&address.to_fixed_bytes()], &self.program_id);
            let seed = bs58::encode(&address.to_fixed_bytes()).into_string();
            let solana_address = Pubkey::create_with_seed(&self.base_account.unwrap(), &seed, &self.program_id).unwrap();

            eprintln!("Not found account for {} => {} (seed {})", &address.to_string(), &solana_address.to_string(), &seed);
            
            match self.get_account.unwrap()(&solana_address) {
                Some(acc) => {
                    eprintln!("Account found");                        
                    eprintln!("Account data len {}", acc.data.len());
                    eprintln!("Account owner {}", acc.owner.to_string());
                   
                    accounts.insert(address, SolidityAccount::new_emulator(solana_address, acc.data, acc.lamports).unwrap());
                },
                None => {
                    eprintln!("Account not found {}", &address.to_string());

                    new_accounts.insert(address);
                }
            }
        } 
    }

/*    pub fn add_alias(&self, address: &H160, pubkey: &Pubkey) {
        debug_print!(&("Add alias ".to_owned() + &address.to_string() + " for " + &pubkey.to_string()));
        for (i, account) in (&self.accounts).iter().enumerate() {
            if account.account_info.key == pubkey {
                let mut aliases = self.aliases.borrow_mut();
                aliases.push((*address, i));
                aliases.sort_by_key(|v| v.0);
                return;
            }
        }
    }*/

    fn get_account_solana_address(&self, address: H160) -> Option<Pubkey> {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            Some(acc) => {
                Some(acc.solana_address)
            },
            None => None,
        }
    }

    pub fn get_contract_ether(&self) -> Option<H160> {
        self.create_acc_if_not_exists(self.contract_id);
        let accounts = self.accounts.borrow();
        match accounts.get(&self.contract_id) {
            Some(acc) => {
                Some(acc.account_data.ether)
            },
            None => None,
        }
    }

    pub fn get_contract_nonce(&self) -> Option<u8> {
        self.create_acc_if_not_exists(self.contract_id);
        let accounts = self.accounts.borrow();
        match accounts.get(&self.contract_id) {
            Some(acc) => {
                Some(acc.account_data.nonce)
            },
            None => None,
        }
    }

    pub fn get_caller_ether(&self) -> Option<H160> {
        self.create_acc_if_not_exists(self.caller_id);
        let accounts = self.accounts.borrow();
        match accounts.get(&self.caller_id) {
            Some(acc) => {
                Some(acc.account_data.ether)
            },
            None => None,
        }
    }

    pub fn get_caller_nonce(&self) -> Option<u8> {
        self.create_acc_if_not_exists(self.caller_id);
        let accounts = self.accounts.borrow();
        match accounts.get(&self.caller_id) {
            Some(acc) => {
                Some(acc.account_data.nonce)
            },
            None => None,
        }
    }

    pub fn get_caller_signer(&self) -> Option<Pubkey> {
        self.create_acc_if_not_exists(self.caller_id);
        let accounts = self.accounts.borrow();
        match accounts.get(&self.caller_id) {
            Some(acc) => {
                Some(acc.account_data.signer)
            },
            None => None,
        }
    }

    fn is_solana_address(&self, code_address: &H160) -> bool {
        *code_address == Self::system_account()
    }

    pub fn system_account() -> H160 {
        H160::from_slice(&[0xffu8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8, 0u8])
    }

    pub fn apply<A, I>(&mut self, values: A, delete_empty: bool, skip_addr: Option<(H160, bool)>) -> Result<(), ProgramError>
            where
                A: IntoIterator<Item=Apply<I>>,
                I: IntoIterator<Item=(H256, H256)>
    {
        let mut accounts = self.accounts.borrow_mut();
        let ether_addr = skip_addr.unwrap_or_else(|| (H160::zero(), true));
        let system_account = Self::system_account();        

        for apply in values {
            match apply {
                Apply::Modify {address, basic, code, storage, reset_storage} => {   
                    if address == system_account {
                        continue;
                    }
                    if ether_addr.1 != true && address == ether_addr.0 {
                        continue;
                    }
                    match accounts.get_mut(&address) {
                        None => return Err(ProgramError::NotEnoughAccountKeys),
                        Some(acc) => {
                            for account in (self.account_infos.unwrap()).iter() {
                                if *account.key == acc.solana_address {
                                    acc.update(account, address, basic.nonce, basic.balance.as_u64(), &code, storage, reset_storage)?;
                                    break;
                                }
                            }
                        },
                    };
                },
                Apply::Delete {address: _} => {},
            }
        };

        //for log in logs {};

        Ok(())
    }
}

impl<'a> Backend for SolanaBackend<'a> {
    fn gas_price(&self) -> U256 { U256::zero() }
    fn origin(&self) -> H160 { self.contract_id }
    fn block_hash(&self, _number: U256) -> H256 { H256::default() }
    fn block_number(&self) -> U256 { self.block_number }
    fn block_coinbase(&self) -> H160 { H160::default() }
    fn block_timestamp(&self) -> U256 { self.block_timestamp }
    fn block_difficulty(&self) -> U256 { U256::zero() }
    fn block_gas_limit(&self) -> U256 { U256::zero() }
    fn chain_id(&self) -> U256 { U256::zero() }
    fn exists(&self, address: H160) -> bool {        
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => false,
            Some(_) => true,
        }
    }
    fn basic(&self, address: H160) -> Basic {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => Basic{balance: U256::zero(), nonce: U256::zero()},
            Some(acc) => Basic{
                balance: (acc.lamports).into(),
                nonce: U256::from(acc.account_data.trx_count),
            },
        }
    }
    fn code_hash(&self, address: H160) -> H256 {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => keccak256_digest(&[]),
            Some(acc) => {
                acc.code(|d| {eprintln!("{}", &hex::encode(&d[0..32])); keccak256_digest(d)})
            },
        }
    }
    fn code_size(&self, address: H160) -> usize {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => 0,
            Some(acc) => {
                acc.code(|d| d.len())
            },
        }
    }
    fn code(&self, address: H160) -> Vec<u8> {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => Vec::new(),
            Some(acc) => {
                acc.code(|d| d.into())
            },
        }
    }
    fn storage(&self, address: H160, index: H256) -> H256 {
        self.create_acc_if_not_exists(address);
        let accounts = self.accounts.borrow();
        match accounts.get(&address) {
            None => H256::default(),
            Some(acc) => {
                let index = index.as_fixed_bytes().into();
                let value = acc.storage(|storage| storage.find(index)).unwrap_or_default();
                if let Some(v) = value {u256_to_h256(v)} else {H256::default()}
            },
        }
    }
    fn create(&self, _scheme: &CreateScheme, _address: &H160) {
        if let CreateScheme::Create2 {caller, code_hash, salt} = _scheme {
            debug_print!(&("CreateScheme2 ".to_owned()+&hex::encode(_address)+" from "+&hex::encode(caller)+" "+&hex::encode(code_hash)+" "+&hex::encode(salt)));
        } else {
            debug_print!("Call create");
        }
    /*    let account = if let CreateScheme::Create2{salt,..} = scheme
                {Pubkey::new(&salt.to_fixed_bytes())} else {Pubkey::default()};
        self.add_alias(address, &account);*/
    }
    fn call_inner(&self,
        code_address: H160,
        _transfer: Option<Transfer>,
        input: Vec<u8>,
        _target_gas: Option<usize>,
        _is_static: bool,
        _take_l64: bool,
        _take_stipend: bool,
    ) -> Option<Capture<(ExitReason, Vec<u8>), Infallible>> {
        // return None;
        if !self.is_solana_address(&code_address) {
            return None;
        }

        debug_print!("Call inner");
        debug_print!(&code_address.to_string());
        debug_print!(&hex::encode(&input));

        let (cmd, input) = input.split_at(1);
        match cmd[0] {
            0 => {
                let (program_id, input) = input.split_at(32);
                let program_id = Pubkey::new(program_id);
        
                let (acc_length, input) = input.split_at(2);
                let acc_length = acc_length.try_into().ok().map(u16::from_be_bytes).unwrap();
                
                let mut accounts = Vec::new();
                for i in 0..acc_length {
                    use arrayref::{array_ref, array_refs};
                    let data = array_ref![input, 35*i as usize, 35];
                    let (translate, signer, writable, pubkey) = array_refs![data, 1, 1, 1, 32];
                    let pubkey = if translate[0] != 0 {
                        let account = self.get_account_solana_address(H160::from_slice(&pubkey[12..]));
                        if account.is_some() {
                            account.unwrap()
                        } else {
                            return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));
                        }
                    } else {
                        Pubkey::new(pubkey)
                    };
                    accounts.push(AccountMeta {
                        is_signer: signer[0] != 0,
                        is_writable: writable[0] != 0,
                        pubkey: pubkey,
                    });
                    debug_print!(&format!("Acc: {}", pubkey));
                };
        
                let (_, input) = input.split_at(35 * acc_length as usize);
                debug_print!(&hex::encode(&input));

                let contract_ether = self.get_contract_ether().unwrap();
                let contract_nonce = self.get_contract_nonce().unwrap();
                let contract_seeds = [contract_ether.as_bytes(), &[contract_nonce]];

                // debug_print!("account_infos");
                // for info in self.account_infos {
                //     debug_print!(&format!("  {}", info.key));
                // };
                let result : solana_sdk::entrypoint::ProgramResult;
                match self.get_caller_ether() {
                    Some(_) => {
                        let caller_ether = self.get_caller_ether().unwrap();
                        let caller_nonce = self.get_caller_nonce().unwrap();
                        let sender_seeds = [caller_ether.as_bytes(), &[caller_nonce]];
                         result = invoke_signed(
                            &Instruction{program_id, accounts: accounts, data: input.to_vec()},
                            &self.account_infos.unwrap(), &[&sender_seeds[..], &contract_seeds[..]]
                        );

                    }
                    None => {
                        result = invoke_signed(
                            &Instruction{program_id, accounts: accounts, data: input.to_vec()},
                            &self.account_infos.unwrap(), &[&contract_seeds[..]]
                        );
                    }
                }
                if let Err(err) = result {
                    debug_print!(&format!("result: {}", err));
                    return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));
                };
                return Some(Capture::Exit((ExitReason::Succeed(evm::ExitSucceed::Stopped), Vec::new())));
            },
            1 => {
                use arrayref::{array_ref, array_refs};
                let data = array_ref![input, 0, 66];
                let (tr_base, tr_owner, base, owner) = array_refs![data, 1, 1, 32, 32];

                let base = if tr_base[0] != 0 {
                    let account = self.get_account_solana_address(H160::from_slice(&base[12..]));
                    if account.is_some() {account.unwrap()}
                    else {return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));}
                } else {Pubkey::new(base)};

                let owner = if tr_owner[0] != 0 {
                    let account = self.get_account_solana_address(H160::from_slice(&owner[12..]));
                    if account.is_some() {account.unwrap()}
                    else {return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));}
                } else {Pubkey::new(owner)};

                let (_, seed) = input.split_at(66);
                let seed = if let Ok(seed) = std::str::from_utf8(&seed) {seed}
                else {return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));};

                let pubkey = if let Ok(pubkey) = Pubkey::create_with_seed(&base, seed.into(), &owner) {pubkey}
                else {return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));};

                debug_print!(&format!("result: {}", &hex::encode(pubkey.as_ref())));
                return Some(Capture::Exit((ExitReason::Succeed(evm::ExitSucceed::Returned), pubkey.as_ref().to_vec())));
            },
            _ => {
                return Some(Capture::Exit((ExitReason::Error(evm::ExitError::InvalidRange), Vec::new())));
            }
        }
    }
}
