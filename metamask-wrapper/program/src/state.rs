//! State transition types

use arrayref::{array_mut_ref, array_ref, array_refs, mut_array_refs};
use solana_sdk::{
    program_error::ProgramError,
    program_pack::{IsInitialized, Pack, Sealed},
    pubkey::Pubkey,
};

/// AccountInfo data. token is id of token, token_program_id is id of associated program, transfer instruction is always 3, and parameters are always same.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct AccountInfo {
    /// Is `true` if this structure has been initialized
    pub eth_acc: [u8;20],
    pub trx_count: u32,
}
impl Sealed for AccountInfo {}
impl IsInitialized for AccountInfo {
    fn is_initialized(&self) -> bool {
        self.trx_count == 0
    }
}
impl Pack for AccountInfo {
    const LEN: usize = 24;
    fn unpack_from_slice(src: &[u8]) -> Result<Self, ProgramError> {
        let src = array_ref![src, 0, 24];
        let (eth_acc, trx_count) =
            array_refs![src, 20, 4];
        Ok(AccountInfo {
            eth_acc: *eth_acc,
            trx_count: u32::from_le_bytes(*trx_count),
        })
    }
    fn pack_into_slice(&self, dst: &mut [u8]) {
        let dst = array_mut_ref![dst, 0, 24];
        let (eth_acc, trx_count) =
            mut_array_refs![dst, 20, 4];
        eth_acc.copy_from_slice(self.eth_acc.as_ref());
        *trx_count = self.trx_count.to_le_bytes();
    }
}

/// TokenInfo data. token is id of token, token_program_id is id of associated program, transfer instruction is always 3, and parameters are always same.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct TokenInfo {
    /// Is `true` if this structure has been initialized
    pub token: Pubkey,
    pub eth_token: [u8;20],
}
impl Sealed for TokenInfo {}
impl IsInitialized for TokenInfo {
    fn is_initialized(&self) -> bool {
        self.token != Pubkey::new(&[0;32])
    }
}
impl Pack for TokenInfo {
    const LEN: usize = 52;
    fn unpack_from_slice(src: &[u8]) -> Result<Self, ProgramError> {
        let src = array_ref![src, 0, 52];
        let (token, eth_token) =
            array_refs![src, 32, 20];
        Ok(TokenInfo {
            token: Pubkey::new_from_array(*token),
            eth_token: *eth_token,
        })
    }
    fn pack_into_slice(&self, dst: &mut [u8]) {
        let dst = array_mut_ref![dst, 0, 52];
        let (token, eth_token) =
            mut_array_refs![dst, 32, 20];
        token.copy_from_slice(self.token.as_ref());
        eth_token.copy_from_slice(self.eth_token.as_ref());
    }
}

/// BalanceInfo data
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct BalanceInfo {
    pub account: Pubkey,
    pub eth_token: [u8;20],
    pub eth_acc: [u8;20],
}
impl Sealed for BalanceInfo {}
impl IsInitialized for BalanceInfo {
    fn is_initialized(&self) -> bool {
        self.account != Pubkey::new(&[0;32])
    }
}
impl Pack for BalanceInfo {
    const LEN: usize = 72;
    fn unpack_from_slice(src: &[u8]) -> Result<Self, ProgramError> {
        let src = array_ref![src, 0, 72];
        let (account, eth_token, eth_acc) = array_refs![src, 32, 20, 20];
        Ok(BalanceInfo {
            account: Pubkey::new_from_array(*account),
            eth_token: *eth_token,
            eth_acc: *eth_acc,
        })
    }
    fn pack_into_slice(&self, dst: &mut [u8]) {
        let dst = array_mut_ref![dst, 0, 72];
        let (account, eth_token, eth_acc) = mut_array_refs![dst, 32, 20, 20];
        account.copy_from_slice(self.account.as_ref());
        eth_token.copy_from_slice(self.eth_token.as_ref());
        eth_acc.copy_from_slice(self.eth_acc.as_ref());
    }
}


