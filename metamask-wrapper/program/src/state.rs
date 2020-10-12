//! State transition types

use arrayref::{array_mut_ref, array_ref, array_refs, mut_array_refs};
use num_enum::TryFromPrimitive;
use solana_sdk::{
    program_error::ProgramError,
    program_pack::{IsInitialized, Pack, Sealed},
    pubkey::Pubkey,
};

/// TokenProgram data. token is id of token, token_program_id is id of associated program, transfer instruction is always 3, and parameters are always same.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct TokenProgram {
    /// Is `true` if this structure has been initialized
    pub is_initialized: bool,
    pub token: Pubkey,
    pub token_program_id: Pubkey,
}
impl Sealed for TokenProgram {}
impl IsInitialized for TokenProgram {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}
impl Pack for TokenProgram {
    const LEN: usize = 65;
    fn unpack_from_slice(src: &[u8]) -> Result<Self, ProgramError> {
        let src = array_ref![src, 0, 65];
        let (is_initialized, token, token_program_id) =
            array_refs![src, 1, 32, 32];
        Ok(Self {
            is_initialized: match is_initialized {
                [0] => false,
                [1] => true,
                _ => return Err(ProgramError::InvalidAccountData),
            },
            token: Pubkey::new_from_array(*token),
            token_program_id: Pubkey::new_from_array(*token_program_id),
        })
    }
    fn pack_into_slice(&self, dst: &mut [u8]) {
        let dst = array_mut_ref![dst, 0, 65];
        let (is_initialized, token, token_program_id) =
            mut_array_refs![dst, 1, 32, 32];
        is_initialized[0] = self.is_initialized as u8;
        token.copy_from_slice(self.token.as_ref());
        token_program_id.copy_from_slice(self.token_program_id.as_ref());
    }
}
