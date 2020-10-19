//! Error types

use num_derive::FromPrimitive;
use solana_sdk::{decode_error::DecodeError, program_error::ProgramError};
use thiserror::Error;

/// Errors that may be returned by the MetamaskWrapper program.
#[derive(Clone, Debug, Eq, Error, FromPrimitive, PartialEq)]
pub enum MetamaskError {
    /// The account cannot be initialized because it is already being used.
    #[error("Same account is already registered")]
    AccountAlreadyRegistered,

    /// The token cannot be initialized because it is already being used.
    #[error("Same token is already registered")]
    TokenAlreadyRegistered,

    /// Balanc cannot be initialized because it is already being used
    #[error("Same balance is already registered")]
    BalanceAlreadyRegistered,

    /// Try to transfer token which is not registered with its program.
    #[error("Token is not registered")]
    TokenNotRegistered,

    /// Invalid instruction number passed in.
    #[error("Invalid instruction")]
    InvalidInstruction,
}
impl From<MetamaskError> for ProgramError {
    fn from(e: MetamaskError) -> Self {
        ProgramError::Custom(e as u32)
    }
}
impl<T> DecodeError<T> for MetamaskError {
    fn type_of() -> &'static str {
        "Metamask Error"
    }
}
