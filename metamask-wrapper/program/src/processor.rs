//! Program state processor

#![cfg(feature = "program")]

use crate::{
    error::MetamaskError,
    instruction::MetamaskInstruction,
    state::TokenInfo,
};
use num_traits::FromPrimitive;
use solana_sdk::instruction::Instruction;
#[cfg(target_arch = "bpf")]
use solana_sdk::program::invoke_signed;
use solana_sdk::{
    account_info::{next_account_info, AccountInfo},
    decode_error::DecodeError,
    entrypoint::ProgramResult,
    info,
    program_error::PrintProgramError,
    program_error::ProgramError,
    program_pack::Pack,
    pubkey::Pubkey,
};
use spl_token::instruction::transfer;

/// Program state handler.
pub struct Processor {}
impl Processor {
    /// Processes an [Initialize](enum.Instruction.html).
    pub fn process_initialize(
        accounts: &[AccountInfo],
        token: &Pubkey,
        eth_token: &[u8;20],
        decimals: u8,
        nonce: u8,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let token_info_acc = next_account_info(account_info_iter)?;
        let program_id = next_account_info(account_info_iter)?;
        let system_id = next_account_info(account_info_iter)?;
        let user = next_account_info(account_info_iter)?;

        info!(&bs58::encode(token_info_acc.key).into_string());
        info!(&bs58::encode(token).into_string());
        info!(&hex::encode(eth_token));

        let seeds = [&eth_token[..20], &[nonce]];
        let signers = &[&seeds[..]];

        let ix = solana_sdk::system_instruction::create_account(
            user.key, 
            token_info_acc.key,
            1000,
            54,
            program_id.key,);
        invoke_signed(&ix, &[token_info_acc.clone(), system_id.clone(), user.clone()], signers);
        info!("Create account done");

        let mut info = TokenInfo::unpack_unchecked(&token_info_acc.data.borrow())?;
        if info.is_initialized {
            return Err(MetamaskError::TokenAlreadyRegistered.into());
        }

        let obj = TokenInfo {
            is_initialized: true,
            token: *token,
            eth_token: *eth_token,
            decimals: decimals,
        };
        TokenInfo::pack(obj, &mut token_info_acc.data.borrow_mut());
        Ok(())
    }

    /// Processes an [Transfer](enum.Instruction.html).
    pub fn process_transfer(
        accounts: &[AccountInfo],
        amount: u64,
        nonce: u8,
        eth_token: &[u8;20],
        eth_acc: &[u8;20],
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();

        let token_program = next_account_info(account_info_iter)?;
        let source = next_account_info(account_info_iter)?;
        let destination = next_account_info(account_info_iter)?;
        let authority = next_account_info(account_info_iter)?;

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

    /// Processes an [Instruction](enum.Instruction.html).
    pub fn process(program_id: &Pubkey, accounts: &[AccountInfo], input: &[u8]) -> ProgramResult {
        let instruction = MetamaskInstruction::unpack(input)?;
        match instruction {
            MetamaskInstruction::Initialize {
                token,
                eth_token,
                decimals,
                nonce,
            } => {
                info!("Instruction: Init");
                Self::process_initialize(
                    accounts,
                    &token,
                    &eth_token,
                    decimals,
                    nonce,
                )
            }
            MetamaskInstruction::Transfer {
                amount, nonce, eth_token, eth_acc,
            } => {
                info!("Instruction: Transfer");
                info!(&hex::encode(&eth_token));
                info!(&hex::encode(&eth_acc));
                Self::process_transfer(
                    accounts, amount, nonce, &eth_token, &eth_acc,
                )
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
            MetamaskError::TokenAlreadyRegistered => info!("Error: Same token is already registered"),
            MetamaskError::TokenNotRegistered => info!("Error: Token is not registered"),
            MetamaskError::InvalidInstruction => info!("Error: InvalidInstruction"),
        }
    }
}

// Pull in syscall stubs when building for non-BPF targets
#[cfg(not(target_arch = "bpf"))]
solana_sdk::program_stubs!();
