//! Program state processor

#![cfg(feature = "program")]

use crate::{
    error::MetamaskError,
    instruction::MetamaskInstruction,
    state::{AccountInfo as AccInfo, TokenInfo, BalanceInfo,},
    eth_transaction::{SignedTransaction, get_tx_sender},
};
use num_traits::FromPrimitive;
#[cfg(target_arch = "bpf")]
use solana_sdk::program::invoke_signed;
use solana_sdk::{
    account_info::{next_account_info, AccountInfo},
    decode_error::DecodeError,
    entrypoint::ProgramResult,
    info,
    program_error::PrintProgramError,
    program_pack::Pack,
    pubkey::Pubkey,
    sysvar::{rent::Rent, Sysvar},
};
pub use ethereum_types::Address;

/// Program state handler.
pub struct Processor {}
impl Processor {
    /// Processes an [InitializeAccount](enum.Instruction.html).
    pub fn process_initialize_account(
        accounts: &[AccountInfo],
        program_id: &Pubkey,
        eth_acc: &[u8;20],
        nonce: u8,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let account_info = next_account_info(account_info_iter)?;
        let system_id = next_account_info(account_info_iter)?;
        let rent_id = next_account_info(account_info_iter)?;
        let user = next_account_info(account_info_iter)?;

        info!(&bs58::encode(account_info.key).into_string());
        info!(&hex::encode(eth_acc));

        let rent = &Rent::from_account_info(rent_id)?;

        let seeds = [&eth_acc[..20], &[nonce]];
        let signers = &[&seeds[..]];

        let ix = solana_sdk::system_instruction::create_account(
            user.key, 
            account_info.key,
            rent.minimum_balance(AccInfo::LEN),
            AccInfo::LEN as u64,
            program_id,);
        invoke_signed(&ix, &[account_info.clone(), system_id.clone(), user.clone()], signers)?;
        info!("Create account done");

        let info = AccInfo::unpack_unchecked(&account_info.data.borrow())?;
        if info.trx_count != 0 {
            return Err(MetamaskError::AccountAlreadyRegistered.into());
        }

        let obj = AccInfo {
            eth_acc: *eth_acc,
            trx_count: 1,
        };
        AccInfo::pack(obj, &mut account_info.data.borrow_mut())?;
        Ok(())
    }

    /// Processes an [InitializeToken](enum.Instruction.html).
    pub fn process_initialize_token(
        accounts: &[AccountInfo],
        program_id: &Pubkey,
        token: &Pubkey,
        eth_token: &[u8;20],
        nonce: u8,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let token_info = next_account_info(account_info_iter)?;
        let system_id = next_account_info(account_info_iter)?;
        let rent_id = next_account_info(account_info_iter)?;
        let user = next_account_info(account_info_iter)?;

        info!(&bs58::encode(token_info.key).into_string());
        info!(&bs58::encode(token).into_string());
        info!(&hex::encode(eth_token));

        let rent = &Rent::from_account_info(rent_id)?;

        let seeds = [&eth_token[..20], &[nonce]];
        let signers = &[&seeds[..]];

        let ix = solana_sdk::system_instruction::create_account(
            user.key, 
            token_info.key,
            rent.minimum_balance(TokenInfo::LEN),
            TokenInfo::LEN as u64,
            program_id,);
        invoke_signed(&ix, &[token_info.clone(), system_id.clone(), user.clone()], signers)?;
        info!("Create account done");

        let info = TokenInfo::unpack_unchecked(&token_info.data.borrow())?;
        if info.token != Pubkey::new(&[0; 32]) {
            return Err(MetamaskError::TokenAlreadyRegistered.into());
        }

        let obj = TokenInfo {
            token: *token,
            eth_token: *eth_token,
        };
        TokenInfo::pack(obj, &mut token_info.data.borrow_mut())?;
        Ok(())
    }

    pub fn process_initialize_balance(
        accounts: &[AccountInfo],
        program_id: &Pubkey,
        account: &Pubkey,
        eth_token: &[u8;20],
        eth_acc: &[u8;20],
        nonce: u8,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let account_info_acc = next_account_info(account_info_iter)?;
        let system_id = next_account_info(account_info_iter)?;
        let rent_id = next_account_info(account_info_iter)?;
        let user = next_account_info(account_info_iter)?;

        let rent = &Rent::from_account_info(rent_id)?;

        let seeds = [&eth_token[..20], &eth_acc[..20], &[nonce]];
        let signers = &[&seeds[..]];

        info!("Process_initialize_balance");
        info!(&nonce.to_string());
        let acc = Pubkey::create_program_address(&seeds, program_id).unwrap();
        info!(&bs58::encode(acc).into_string());

        let ix = solana_sdk::system_instruction::create_account(
            user.key, 
            account_info_acc.key,
            rent.minimum_balance(BalanceInfo::LEN),
            BalanceInfo::LEN as u64,
            program_id,);
        invoke_signed(&ix, &[account_info_acc.clone(), system_id.clone(), user.clone()], signers)?;
        info!("Create account done");

        let info = BalanceInfo::unpack_unchecked(&account_info_acc.data.borrow())?;
        if info.account != Pubkey::new(&[0;32]) {
            return Err(MetamaskError::BalanceAlreadyRegistered.into());
        }

        let obj = BalanceInfo {
            account: *account,
            eth_token: *eth_token,
            eth_acc: *eth_acc,
        };
        BalanceInfo::pack(obj, &mut account_info_acc.data.borrow_mut())?;
        Ok(())
    }

    /// Processes an [Transfer](enum.Instruction.html).
    pub fn process_transfer(
        accounts: &[AccountInfo],
        amount: u64,
        nonce: u8,
        eth_token: &[u8;20],
        eth_acc: &[u8;20],
        eth_tx: &Vec<u8>,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();

        let token_program = next_account_info(account_info_iter)?;
        let source = next_account_info(account_info_iter)?;
        let destination = next_account_info(account_info_iter)?;
        let authority = next_account_info(account_info_iter)?;

        let eth_tx_decoded: Result<SignedTransaction, _> = rlp::decode(&eth_tx);
        if eth_tx_decoded.is_err() {
            return Err(MetamaskError::EthereumTxInvalidFormat.into());
        }
        if get_tx_sender(&eth_tx_decoded.unwrap()).unwrap() != Address::from_slice(eth_acc) {
            return Err(MetamaskError::EthereumTxSignedWrong.into());
        }

        let seeds = [&eth_token[..20], &eth_acc[..20], &[nonce]];
        let signers = &[&seeds[..]];
        let ix = spl_token::instruction::transfer(
            token_program.key,
            source.key,
            destination.key,
            authority.key,
            &[],
            amount,
        )?;
        invoke_signed(
            &ix,
            &[source.clone(), destination.clone(), authority.clone(), token_program.clone()],
            signers,
        )
    }

    /// Processes an [TransferLamports](enum.Instruction.html).
    pub fn process_transfer_lamports(
        accounts: &[AccountInfo],
        amount: u64,
        nonce: u8,
        eth_acc: &[u8;20],
        eth_tx: &Vec<u8>,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();

        let source = next_account_info(account_info_iter)?;
        let destination = next_account_info(account_info_iter)?;
        let system_id = next_account_info(account_info_iter)?;

        let eth_tx_decoded: Result<SignedTransaction, _> = rlp::decode(&eth_tx);
        if eth_tx_decoded.is_err() {
            return Err(MetamaskError::EthereumTxInvalidFormat.into());
        }
        if get_tx_sender(&eth_tx_decoded.unwrap()).unwrap() == Address::from([0x02u8; 20]) {
            return Err(MetamaskError::EthereumTxSignedWrong.into());
        }
        Ok(())
/*
        let seeds = [&eth_acc[..20], "lamports".as_ref(), &[nonce]];
        let signers = &[&seeds[..]];
        let ix = solana_sdk::system_instruction::transfer(
            source.key,
            destination.key,
            amount,
        );
        invoke_signed(
            &ix,
            &[source.clone(), destination.clone(), system_id.clone()],
            signers,
        )*/
    }

    /// Processes an [Instruction](enum.Instruction.html).
    pub fn process(program_id: &Pubkey, accounts: &[AccountInfo], input: &[u8]) -> ProgramResult {
        let instruction = MetamaskInstruction::unpack(input)?;
        match instruction {
            MetamaskInstruction::InitializeAccount {eth_acc, nonce,} => {
                info!("Instruction: Initialize account");
                Self::process_initialize_account(accounts, &program_id, &eth_acc, nonce,)
            }
            MetamaskInstruction::InitializeToken {token, eth_token, nonce,} => {
                info!("Instruction: Initialize token");
                Self::process_initialize_token(accounts, &program_id, &token, &eth_token, nonce,)
            }
            MetamaskInstruction::InitializeBalance {account, eth_token, eth_acc, nonce,} => {
                info!("Instruction: Initialize balance");
                info!(&hex::encode(&eth_token));
                info!(&hex::encode(&eth_acc));
                Self::process_initialize_balance(accounts, &program_id, &account, &eth_token, &eth_acc, nonce,)
            }
            MetamaskInstruction::Transfer {amount, nonce, eth_token, eth_acc, eth_tx,} => {
                info!("Instruction: Transfer");
                info!(&hex::encode(&eth_token));
                info!(&hex::encode(&eth_acc));
                Self::process_transfer(
                    accounts, amount, nonce, &eth_token, &eth_acc, &eth_tx,
                )
            }
            MetamaskInstruction::TransferLamports {amount, nonce, eth_acc, eth_tx,} => {
                Self::process_transfer_lamports(accounts, amount, nonce, &eth_acc, &eth_tx,)
            }
        }
    }
}

impl PrintProgramError for MetamaskError {
    fn print<E>(&self)
    where
        E: 'static + std::error::Error + DecodeError<E> + PrintProgramError + FromPrimitive,
    {
        match self {
            MetamaskError::AccountAlreadyRegistered => info!("Error: Same account is already registered"),
            MetamaskError::TokenAlreadyRegistered => info!("Error: Same token is already registered"),
            MetamaskError::BalanceAlreadyRegistered => info!("Error: Same balance is already registered"),
            MetamaskError::TokenNotRegistered => info!("Error: Token is not registered"),
            MetamaskError::EthereumTxInvalidFormat => info!("Error: Ethereum transaction has invalid format"),
            MetamaskError::EthereumTxSignedWrong => info!("Error: Ethereum transaction has wrong signature"),
            MetamaskError::InvalidInstruction => info!("Error: InvalidInstruction"),
        }
    }
}

// Pull in syscall stubs when building for non-BPF targets
#[cfg(not(target_arch = "bpf"))]
solana_sdk::program_stubs!();
