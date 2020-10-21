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
    /// Initialize info about Ethereum account.
    ///
    /// The `InitializeAccount` instruction create new account and initialize
    /// info about Ethereum account. New account address derived from
    /// create_program_address([eth_acc], program_id).
    ///
    /// Accounts expected by this instruction:
    ///
    ///   0. `[writable]` account_info (derived from create_program_address([eth_acc], program_id))
    ///   1. `[]` system program id
    ///   2. `[]` rent program id
    ///   3. `[signer]` creator of new account
    ///
    InitializeAccount {
        /// Ethereum account
        eth_acc: [u8;20],
        /// Nonce derived from find_program_address([eth_acc], program_id)
        nonce: u8,
    },

    /// Initialize info about Ethereum token.
    ///
    /// The `InitializeToken` instruction create new account and initialize
    /// info about Ethereum token. New account address derived from
    /// create_program_address([eth_token], program_id).
    ///
    /// Accounts expected by this instruction:
    ///
    ///   0. `[writable]` token_info (derived from create_program_address([eth_token], program_id))
    ///   1. `[]` system program id
    ///   2. `[]` rent program id
    ///   3. `[signer]` creator of new account
    ///
    InitializeToken {
        /// Solana token address
        token: Pubkey,
        /// Ethereum token address
        eth_token: [u8;20],
        /// Nonce derived from find_program_address([eth_token], program_id)
        nonce: u8,
    },

    /// Initialize info about Ethereum account balance.
    ///
    /// The `InitializeBalance` instruction create new account and initialize
    /// info about Ethereum account balance. New account address derived from
    /// create_program_address([eth_token, eth_acc], program_id).
    ///
    /// Accounts expected by this instruction:
    ///
    ///   0. `[writable]` account_info (derived from create_program_address([eth_acc], program_id))
    ///   1. `[]` system program id
    ///   2. `[]` rent program id
    ///   3. `[signer]` creator of new account
    ///
    InitializeBalance {
        /// Account with Solana token balance
        account: Pubkey,
        /// Ethereum token address
        eth_token: [u8;20],
        /// Etehreum account address
        eth_acc: [u8;20],
        /// Nonce derived from find_program_address([eth_token, eth_acc], program_id)
        nonce: u8,
    },

    /// Transfer token from Ethereum account balance.
    ///
    /// Accounts expected by this instruction:
    ///
    ///   0. `[]` token program id
    ///   1. `[writable]` source account (must be owned by authority)
    ///   2. `[writable]` destination account
    ///   3. `[]` authority for source account (derived from create_program_address([eth_token, eth_acc], program_id))
    ///
    Transfer {
        /// The amount of tokens to transfer
        amount: u64,
        /// Nonce derived from find_program_address([eth_token, eth_acc], program_id)
        nonce: u8,
        /// Ethereum token address
        eth_token: [u8;20],
        /// Ethereum source account address
        eth_acc: [u8;20],
        /// Ethereum transaction binary data
        eth_tx: Vec<u8>
    },

    /// Transfer lamports from Ethereum account.
    ///
    /// Accounts expected by this instruction:
    ///
    ///   0. `[writable]` source account (derived from create_program_address([eth_acc, 'lamports'], program_id))
    ///   1. `[writable]` destination account
    ///   2. `[]` system_id
    TransferLamports {
        /// The amount of lamports to transfer
        amount: u64,
        /// Nonce derived from find_program_address([eth_acc, 'lamports'], program_id)
        nonce: u8,
        /// Ethereum source account address
        eth_acc: [u8;20],
        /// Ethereum transaction binary data
        eth_tx: Vec<u8>
    },
}

impl MetamaskInstruction {
    /// Unpacks a byte buffer into a [MetamaskInstruction](enum.MetamaskInstruction.html).
    pub fn unpack(input: &[u8]) -> Result<Self, ProgramError> {
        let (&tag, rest) = input.split_first().ok_or(MetamaskError::InvalidInstruction)?;
        Ok(match tag {
            0 => {     // Initialize account
                let (eth_acc_slice, rest) = rest.split_at(20);
                let (&nonce, _rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_acc: [u8;20] = Default::default();
                eth_acc.copy_from_slice(&eth_acc_slice);

                Self::InitializeAccount {eth_acc, nonce,}
            }
            1 => {     // Initialize token
                let (token, rest) = Self::unpack_pubkey(rest)?;
                let (eth_token_slice, rest) = rest.split_at(20);
                let (&nonce, _rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_token: [u8;20] = Default::default();
                eth_token.copy_from_slice(&eth_token_slice);

                Self::InitializeToken {token, eth_token, nonce,}
            }
            2 => {     // Initialize balance
                let (account, rest) = Self::unpack_pubkey(rest)?;
                let (eth_token_slice, rest) = rest.split_at(20);
                let (eth_acc_slice, rest) = rest.split_at(20);
                let (&nonce, _rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_token: [u8;20] = Default::default();
                let mut eth_acc: [u8;20] = Default::default();
                eth_token.copy_from_slice(&eth_token_slice);
                eth_acc.copy_from_slice(&eth_acc_slice);

                Self::InitializeBalance {account, eth_token, eth_acc, nonce,}
            }
            3 => {
                let (amount, rest) = rest.split_at(8);
                let (&nonce, rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;
                let (eth_token_slice, rest) = rest.split_at(20);
                let (eth_acc_slice, _rest) = rest.split_at(20);
                let amount = amount
                    .try_into()
                    .ok()
                    .map(u64::from_le_bytes)
                    .ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_token : [u8; 20] = Default::default();
                let mut eth_acc : [u8; 20] = Default::default();
                let mut eth_tx = Vec::new();
                eth_token.copy_from_slice(&eth_token_slice);
                eth_acc.copy_from_slice(&eth_acc_slice);
                eth_tx.extend_from_slice(&_rest);

                Self::Transfer {amount, nonce, eth_token, eth_acc, eth_tx,}
            }
            4 => {
                let (amount, rest) = rest.split_at(8);
                let (&nonce, rest) = rest.split_first().ok_or(MetamaskError::InvalidInstruction)?;
                let (eth_acc_slice, _rest) = rest.split_at(20);
                let amount = amount
                    .try_into()
                    .ok()
                    .map(u64::from_le_bytes)
                    .ok_or(MetamaskError::InvalidInstruction)?;

                let mut eth_acc : [u8; 20] = Default::default();
                let mut eth_tx = Vec::new();
                eth_acc.copy_from_slice(&eth_acc_slice);
                eth_tx.extend_from_slice(&_rest);

                Self::TransferLamports {amount, nonce, eth_acc, eth_tx,}
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
        match &*self {
            Self::InitializeAccount {eth_acc, nonce,} => {
                buf.push(0);
                buf.extend_from_slice(eth_acc);
                buf.push(*nonce);
            }
            Self::InitializeToken {token, eth_token, nonce,} => {
                buf.push(1);
                buf.extend_from_slice(token.as_ref());
                buf.extend_from_slice(eth_token);
                buf.push(*nonce);
            }
            Self::InitializeBalance {account, eth_token, eth_acc, nonce,} => {
                buf.push(2);
                buf.extend_from_slice(account.as_ref());
                buf.extend_from_slice(eth_token);
                buf.extend_from_slice(eth_acc);
                buf.push(*nonce);
            }
            Self::Transfer {amount, nonce, eth_token, eth_acc, eth_tx,} => {
                buf.push(3);
                buf.extend_from_slice(&amount.to_le_bytes());
                buf.push(*nonce);
                buf.extend_from_slice(eth_token);
                buf.extend_from_slice(eth_acc);
                buf.extend_from_slice(eth_tx);
            }
            Self::TransferLamports {amount, nonce, eth_acc, eth_tx,} => {
                buf.push(4);
                buf.extend_from_slice(&amount.to_le_bytes());
                buf.push(*nonce);
                buf.extend_from_slice(eth_acc);
                buf.extend_from_slice(eth_tx);
            }
        }
        buf
    }
}

/// Creates an 'initialize' instruction.
pub fn initialize_account(
    wrapper_program: &Pubkey,
    account_info: &Pubkey,
    eth_acc: &[u8;20],
    nonce: u8,
) -> Result<Instruction, ProgramError> {
    let init_data = MetamaskInstruction::InitializeAccount {
        eth_acc: *eth_acc,
        nonce: nonce,
    };
    let data = init_data.pack();

    let accounts = vec![
        AccountMeta::new(*account_info, false),
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
    eth_tx: Vec<u8>,
) -> Result<Instruction, ProgramError> {
    let data = MetamaskInstruction::Transfer { amount, nonce, eth_token, eth_acc, eth_tx }.pack();

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
