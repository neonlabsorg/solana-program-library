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
    Initialize {
        token: Pubkey,
        eth_token: [u8;20],
        decimals: u8,
        nonce: u8,
    },
    Transfer {
        amount: u64,
        nonce: u8,
        eth_token: [u8;20],
        eth_acc: [u8;20],
    }
}

impl MetamaskInstruction {
    /// Unpacks a byte buffer into a [MetamaskInstruction](enum.MetamaskInstruction.html).
    pub fn unpack(input: &[u8]) -> Result<Self, ProgramError> {
        let (&tag, rest) = input.split_first().ok_or(MetamaskError::InvalidInstruction)?;
        Ok(match tag {
            0 => {
                let (token, rest) = Self::unpack_pubkey(rest)?;
                let (eth_token_slice, rest) = rest.split_at(20);
                let (&decimals, rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;
                let (&nonce, rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_token: [u8;20] = Default::default();
                eth_token.copy_from_slice(&eth_token_slice);

                Self::Initialize {token, eth_token, decimals, nonce,}
            }
            3 => {
                let (amount, rest) = rest.split_at(8);
                let (&nonce, rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;
                let (eth_token_slice, rest) = rest.split_at(20);
                let (eth_acc_slice, rest) = rest.split_at(20);
                let amount = amount
                    .try_into()
                    .ok()
                    .map(u64::from_le_bytes)
                    .ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_token : [u8; 20] = Default::default();
                let mut eth_acc : [u8; 20] = Default::default();
                eth_token.copy_from_slice(&eth_token_slice);
                eth_acc.copy_from_slice(&eth_acc_slice);

                Self::Transfer {amount, nonce, eth_token, eth_acc,}
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
            Self::Initialize {
                token,
                eth_token,
                decimals,
                nonce,
            } => {
                buf.push(0);
                buf.extend_from_slice(token.as_ref());
                buf.extend_from_slice(eth_token.as_ref());
                buf.push(decimals);
                buf.push(nonce,)
            }
            Self::Transfer { amount, nonce, eth_token, eth_acc } => {
                buf.push(3);
                buf.extend_from_slice(&amount.to_le_bytes());
                buf.push(nonce);
                buf.extend_from_slice(&eth_token);
                buf.extend_from_slice(&eth_acc);
            }
        }
        buf
    }
}

/// Creates an 'initialize' instruction.
pub fn initialize(
    wrapper_program: &Pubkey,
    token_info: &Pubkey,
    token: &Pubkey,
    eth_token: &[u8;20],
    decimals: u8,
    nonce: u8,
) -> Result<Instruction, ProgramError> {
    let init_data = MetamaskInstruction::Initialize {
        token: *token,
        eth_token: *eth_token,
        decimals: decimals,
        nonce: nonce,
    };
    let data = init_data.pack();

    let accounts = vec![
        AccountMeta::new(*token_info, false),
    ];

    Ok(Instruction {
        program_id: *wrapper_program,
        accounts,
        data,
    })
}

/// Creates a `Transfer` instruction.
pub fn transfer(
    program_id: &Pubkey,
    source_pubkey: &Pubkey,
    destination_pubkey: &Pubkey,
    authority_pubkey: &Pubkey,
    amount: u64,
    nonce: u8,
    eth_token: [u8; 20],
    eth_acc: [u8; 20],
) -> Result<Instruction, ProgramError> {
    let data = MetamaskInstruction::Transfer { amount, nonce, eth_token, eth_acc }.pack();

    let mut accounts = Vec::with_capacity(4);
    accounts.push(AccountMeta::new(*program_id, false));
    accounts.push(AccountMeta::new(*source_pubkey, false));
    accounts.push(AccountMeta::new(*destination_pubkey, false));
    accounts.push(AccountMeta::new_readonly(*authority_pubkey, false));

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
