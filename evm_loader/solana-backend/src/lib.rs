#[macro_use]
mod debug;
pub mod solana_backend;
mod solidity_account;
mod account_data;
mod hamt;
pub mod constatns;

pub use solana_sdk;

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4);
    }
}
