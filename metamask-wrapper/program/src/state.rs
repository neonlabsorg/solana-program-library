//! State transition types

use arrayref::{array_mut_ref, array_ref, array_refs, mut_array_refs};
use num_enum::TryFromPrimitive;
use solana_sdk::{
    program_error::ProgramError,
    program_pack::{IsInitialized, Pack, Sealed},
    pubkey::Pubkey,
};

/// TokenInfo data. token is id of token, token_program_id is id of associated program, transfer instruction is always 3, and parameters are always same.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct TokenInfo {
    /// Is `true` if this structure has been initialized
    pub is_initialized: bool,
    pub token: Pubkey,
    pub eth_token: [u8;20],
    pub decimals: u8,
}
impl Sealed for TokenInfo {}
impl IsInitialized for TokenInfo {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}
impl Pack for TokenInfo {
    const LEN: usize = 54;
    fn unpack_from_slice(src: &[u8]) -> Result<Self, ProgramError> {
        let src = array_ref![src, 0, 54];
        let (is_initialized, token, eth_token, decimals) =
            array_refs![src, 1, 32, 20, 1];
        Ok(TokenInfo {
            is_initialized: match is_initialized {
                [0] => false,
                [1] => true,
                _ => false,
            },
            token: Pubkey::new_from_array(*token),
            eth_token: *eth_token,
            decimals: decimals[0],
        })
    }
    fn pack_into_slice(&self, dst: &mut [u8]) {
        let dst = array_mut_ref![dst, 0, 54];
        let (is_initialized, token, eth_token, decimals) =
            mut_array_refs![dst, 1, 32, 20, 1];
        is_initialized[0] = self.is_initialized as u8;
        token.copy_from_slice(self.token.as_ref());
        eth_token.copy_from_slice(self.eth_token.as_ref());
        decimals[0] = self.decimals as u8;
    }
}


