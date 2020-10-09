//! Program state processor

#![cfg(feature = "program")]

use crate::{
    error::MetamaskError,
    instruction::MetamaskInstruction,
    state::TokenProgram,
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
        accounts: &[AccountInfo]
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let token_info = next_account_info(account_info_iter)?;
        let program_info = next_account_info(account_info_iter)?;

        let token_prog = TokenProgram::unpack(&token_info.data.borrow())?;
        if token_prog.is_initialized {
            return Err(MetamaskError::TokenAlreadyRegistered.into());
        }

        let obj = TokenProgram {
            is_initialized: true,
            token: *(token_info.key),
            token_program_id: *(program_info.key),
        };
        TokenProgram::pack(obj, &mut token_info.data.borrow_mut());
        Ok(())
    }
    /// Processes an [Transfer](enum.Instruction.html).
    pub fn process_transfer(
        accounts: &[AccountInfo],
        amount: u64,
    ) -> ProgramResult {
        let account_info_iter = &mut accounts.iter();
        let token_info = next_account_info(account_info_iter)?;

        let token_prog = TokenProgram::unpack(&token_info.data.borrow())?;
        if !token_prog.is_initialized {
            return Err(MetamaskError::TokenNotRegistered.into());
        }
        let ix = spl_token::instruction::transfer(
            &token_prog.token_program_id,
            &token_prog.token_program_id,
            &token_prog.token_program_id,
            &token_prog.token_program_id,
            &[],
            amount,
        )?;
        invoke_signed(
            &ix,
            accounts,
            &[],
        )
    }
    /// Processes an [Instruction](enum.Instruction.html).
    pub fn process(program_id: &Pubkey, accounts: &[AccountInfo], input: &[u8]) -> ProgramResult {
        let instruction = MetamaskInstruction::unpack(input)?;
        match instruction {
            MetamaskInstruction::Initialize {
                token,
                program,
            } => {
                info!("Instruction: Init");
                Self::process_initialize(
                    accounts,
                    &token,
                    &program,
                )
            }
            MetamaskInstruction::Transfer {
                amount,
            } => {
                info!("Instruction: Transfer");
                Self::process_transfer(
                    accounts,
                    amount,
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
