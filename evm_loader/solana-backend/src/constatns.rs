use num_traits::{FromPrimitive};
use thiserror::Error;

/// Allows customer errors to be decoded back to their original enum
pub trait DecodeError<E> {
    fn decode_custom_error_to_enum(custom: u32) -> Option<E>
    where
        E: FromPrimitive,
    {
        E::from_u32(custom)
    }
    fn type_of() -> &'static str;
}

/// Reasons the program may fail
#[derive(Clone, Debug, Eq, Error, PartialEq)]
pub enum ProgramError {
    /// Allows on-chain programs to implement program-specific error types and see them returned
    /// by the Solana runtime. A program-specific error may be any type that is represented as
    /// or serialized to a u32 integer.
    #[error("Custom program error: {0:#x}")]
    Custom(u32),
    #[error("The arguments provided to a program instruction where invalid")]
    InvalidArgument,
    #[error("An instruction's data contents was invalid")]
    InvalidInstructionData,
    #[error("An account's data contents was invalid")]
    InvalidAccountData,
    #[error("An account's data was too small")]
    AccountDataTooSmall,
    #[error("An account's balance was too small to complete the instruction")]
    InsufficientFunds,
    #[error("The account did not have the expected program id")]
    IncorrectProgramId,
    #[error("A signature was required but not found")]
    MissingRequiredSignature,
    #[error("An initialize instruction was sent to an account that has already been initialized")]
    AccountAlreadyInitialized,
    #[error("An attempt to operate on an account that hasn't been initialized")]
    UninitializedAccount,
    #[error("The instruction expected additional account keys")]
    NotEnoughAccountKeys,
    #[error("Failed to borrow a reference to account data, already borrowed")]
    AccountBorrowFailed,
    #[error("Length of the seed is too long for address generation")]
    MaxSeedLengthExceeded,
    #[error("Provided seeds do not result in a valid address")]
    InvalidSeeds,
}

pub trait PrintProgramError {
    fn print<E>(&self)
    where
        E: 'static + std::error::Error + DecodeError<E> + PrintProgramError + FromPrimitive;
}

impl PrintProgramError for ProgramError {
    fn print<E>(&self)
    where
        E: 'static + std::error::Error + DecodeError<E> + PrintProgramError + FromPrimitive,
    {
        match self {
            Self::Custom(error) => {
                if let Some(custom_error) = E::decode_custom_error_to_enum(*error) {
                    custom_error.print::<E>();
                } else {
                    debug_print!("Error: Unknown");
                }
            }
            Self::InvalidArgument => debug_print!("Error: InvalidArgument"),
            Self::InvalidInstructionData => debug_print!("Error: InvalidInstructionData"),
            Self::InvalidAccountData => debug_print!("Error: InvalidAccountData"),
            Self::AccountDataTooSmall => debug_print!("Error: AccountDataTooSmall"),
            Self::InsufficientFunds => debug_print!("Error: InsufficientFunds"),
            Self::IncorrectProgramId => debug_print!("Error: IncorrectProgramId"),
            Self::MissingRequiredSignature => debug_print!("Error: MissingRequiredSignature"),
            Self::AccountAlreadyInitialized => debug_print!("Error: AccountAlreadyInitialized"),
            Self::UninitializedAccount => debug_print!("Error: UninitializedAccount"),
            Self::NotEnoughAccountKeys => debug_print!("Error: NotEnoughAccountKeys"),
            Self::AccountBorrowFailed => debug_print!("Error: AccountBorrowFailed"),
            Self::MaxSeedLengthExceeded => debug_print!("Error: MaxSeedLengthExceeded"),
            Self::InvalidSeeds => debug_print!("Error: InvalidSeeds"),
        }
    }
}