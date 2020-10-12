//! Instruction types

#![allow(clippy::too_many_arguments)]

use crate::error::MetamaskError;
use solana_sdk::{
    instruction::{AccountMeta, Instruction},
    program_error::ProgramError,
    pubkey::Pubkey,
};
use std::convert::TryInto;
use std::mem::size_of;

/// Instructions supported by the MetamaskWrapper program.
#[repr(C)]
#[derive(Clone, Debug, PartialEq)]
pub enum MetamaskInstruction {
    /// Accounts expected by this instruction:
    ///
    ///   0. `[writable]`  The token to initialize.
    ///   1. `[]` The program to initialize with this token.
    Initialize,
    Transfer {
        amount: u64,
    }
}

impl MetamaskInstruction {
    /// Unpacks a byte buffer into a [MetamaskInstruction](enum.MetamaskInstruction.html).
    pub fn unpack(input: &[u8]) -> Result<Self, ProgramError> {
        let (&tag, rest) = input.split_first().ok_or(MetamaskError::InvalidInstruction)?;
        Ok(match tag {
            0 => Self::Initialize,
            3 => {
                let (amount, rest) = rest.split_at(8);
                let amount = amount
                    .try_into()
                    .ok()
                    .map(u64::from_le_bytes)
                    .ok_or(MetamaskError::InvalidInstruction)?;
                Self::Transfer {
                    amount,
                }
            }
            _ => return Err(MetamaskError::InvalidInstruction.into()),
        })
    }

    fn unpack_pubkey(input: &[u8]) -> Result<(Pubkey, &[u8]), ProgramError> {
        if input.len() >= 32 {
            let (key, rest) = input.split_at(32);
            let pk = Pubkey::new(key);
            Ok((pk, rest))
        } else {
            Err(MetamaskError::InvalidInstruction.into())
        }
    }

    /// Packs a [MetamaskInstruction](enum.MetamaskInstruction.html) into a byte buffer.
    pub fn pack(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(size_of::<Self>());
        match *self {
            Self::Initialize => {
                buf.push(0);
            }
            Self::Transfer { amount } => {
                buf.push(3);
                buf.extend_from_slice(&amount.to_le_bytes());
            }
        }
        buf
    }
}

/// Creates an 'initialize' instruction.
pub fn initialize(
    program_id: &Pubkey,
    token: &Pubkey,
    token_program_id: &Pubkey,
) -> Result<Instruction, ProgramError> {
    let init_data = MetamaskInstruction::Initialize;
    let data = init_data.pack();

    let accounts = vec![
        AccountMeta::new(*token, false),
        AccountMeta::new(*token_program_id, false),
    ];

    Ok(Instruction {
        program_id: *program_id,
        accounts,
        data,
    })
}

/// Creates a `Transfer` instruction.
pub fn transfer(
    program_id: &Pubkey,
    token_id: &Pubkey,
    source_pubkey: &Pubkey,
    destination_pubkey: &Pubkey,
    authority_pubkey: &Pubkey,
    signer_pubkeys: &[&Pubkey],
    amount: u64,
) -> Result<Instruction, ProgramError> {
    let data = MetamaskInstruction::Transfer { amount }.pack();

    let mut accounts = Vec::with_capacity(4+ signer_pubkeys.len());
    accounts.push(AccountMeta::new(*token_id, false));
    accounts.push(AccountMeta::new(*source_pubkey, false));
    accounts.push(AccountMeta::new(*destination_pubkey, false));
    accounts.push(AccountMeta::new_readonly(
        *authority_pubkey,
        signer_pubkeys.is_empty(),
    ));
    for signer_pubkey in signer_pubkeys.iter() {
        accounts.push(AccountMeta::new_readonly(**signer_pubkey, true));
    }

    Ok(Instruction {
        program_id: *program_id,
        accounts,
        data,
    })
}

/// Unpacks a reference from a bytes buffer.
/// TODO actually pack / unpack instead of relying on normal memory layout.
pub fn unpack<T>(input: &[u8]) -> Result<&T, ProgramError> {
    if input.len() < size_of::<u8>() + size_of::<T>() {
        return Err(ProgramError::InvalidAccountData);
    }
    #[allow(clippy::cast_ptr_alignment)]
    let val: &T = unsafe { &*(&input[1] as *const u8 as *const T) };
    Ok(val)
}
