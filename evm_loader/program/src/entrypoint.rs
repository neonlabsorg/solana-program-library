//! Program entrypoint

#![cfg(feature = "program")]
#![cfg(not(feature = "no-entrypoint"))]

//use crate::{error::TokenError, processor::Processor};
//use arrayref::{array_ref, array_refs, array_mut_ref, mut_array_refs};
use std::convert::TryInto;
use solana_sdk::{
    account_info::{next_account_info, AccountInfo},
    entrypoint, entrypoint::{ProgramResult},
    program_error::{ProgramError}, pubkey::Pubkey,
    program_utils::{limited_deserialize},
    loader_instruction::LoaderInstruction,
    system_instruction::{create_account, create_account_with_seed},
    sysvar::instructions::{load_current_index, load_instruction_at}, 
    program::{invoke_signed, invoke},
    info,
    secp256k1_program,
    instruction::Instruction,
    sysvar::instructions
};

//use crate::hamt::Hamt;
// use crate::solana_backend::{
//     SolanaBackend, solidity_address,
// };

use crate::{
//    bump_allocator::BumpAllocator,
    instruction::EvmInstruction,
    // account_data::AccountData,
    // solidity_account::SolidityAccount,
    transaction::{check_tx, make_secp256k1_instruction},
};

use evm::{
//    backend::{MemoryVicinity, MemoryAccount, MemoryBackend, Apply},
    executor::{StackExecutor},
    ExitReason,
};
use primitive_types::{U256};

use std::{alloc::Layout, mem::size_of, ptr::null_mut, usize};
// use solana_sdk::entrypoint::HEAP_START_ADDRESS;
/// Start address of the memory region used for program heap.
pub const HEAP_START_ADDRESS: usize = 12884901888; // 0x0_000_000_300_000_000usize


use sha3::{Keccak256, Digest};
use primitive_types::H256;
fn keccak256_digest(data: &[u8]) -> H256 {
    H256::from_slice(Keccak256::digest(&data).as_slice())
}

use impl_serde::rustc_hex::ToHex;

const HEAP_LENGTH: usize = 1024*1024;

/// Developers can implement their own heap by defining their own
/// `#[global_allocator]`.  The following implements a dummy for test purposes
/// but can be flushed out with whatever the developer sees fit.
pub struct BumpAllocator;

impl BumpAllocator {
    /// Get occupied memory
    #[inline]
    pub fn occupied() -> usize {
        const POS_PTR: *mut usize = HEAP_START_ADDRESS as *mut usize;
        const TOP_ADDRESS: usize = HEAP_START_ADDRESS + HEAP_LENGTH;

        let pos = unsafe{*POS_PTR};
        if pos == 0 {0} else {TOP_ADDRESS-pos}
    }
}

unsafe impl std::alloc::GlobalAlloc for BumpAllocator {
    #[inline]
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        const POS_PTR: *mut usize = HEAP_START_ADDRESS as *mut usize;
        const TOP_ADDRESS: usize = HEAP_START_ADDRESS + HEAP_LENGTH;
        const BOTTOM_ADDRESS: usize = HEAP_START_ADDRESS + size_of::<*mut u8>();

        let mut pos = *POS_PTR;
        if pos == 0 {
            // First time, set starting position
            pos = TOP_ADDRESS;
        }
        pos = pos.saturating_sub(layout.size());
        pos &= !(layout.align().saturating_sub(1));
        if pos < BOTTOM_ADDRESS {
            return null_mut();
        }

        *POS_PTR = pos;
        pos as *mut u8
    }
    #[inline]
    unsafe fn dealloc(&self, _: *mut u8, _layout: Layout) {
        // I'm a bump allocator, I don't free
    }
}


#[cfg(target_arch = "bpf")]
#[global_allocator]
static mut A: BumpAllocator = BumpAllocator;

// Is't need to save for account:
// 1. ether: [u8;20]
// 2. nonce: u8
// 3. trx_count: u128
// 4. signer: pubkey
// 5. code_size: u32
// 6. storage (all remaining space, if code_size not equal zero)

entrypoint!(process_instruction);
fn process_instruction<'a>(
    program_id: &Pubkey,
    accounts: &'a [AccountInfo<'a>],
    instruction_data: &[u8],
) -> ProgramResult {

    let account_info_iter = &mut accounts.iter();

    let instruction = EvmInstruction::unpack(instruction_data)?;
    info!("Instruction parsed");

    let result = match instruction {
        EvmInstruction::CreateAccount {lamports, space, ether, nonce} => {
            Ok(())
        },
        EvmInstruction::CreateAccountWithSeed {base, seed, lamports, space, owner} => {
            Ok(())
        },
        EvmInstruction::Write {offset, bytes} => {
            Ok(())
        },
        EvmInstruction::Finalize => {
            Ok(())
        },
        EvmInstruction::Call {bytes} => {
            Ok(())
        },
        EvmInstruction::CheckEtheriumTX {raw_tx} => {
            check_tx(raw_tx)
        },
        EvmInstruction::CheckEtheriumTXCallProgram {message, sign, eth_addr} => {
            let account_info_iter = &mut accounts.iter();
            let program_account = next_account_info(account_info_iter)?;
            let secp256_account = next_account_info(account_info_iter)?;
            let sysvara_account = next_account_info(account_info_iter)?;  
            
            print_data(&sysvara_account.try_borrow_data()?);
                    
            info!(&( "message: ".to_owned() + &hex::encode(&message)));
            info!(&("    sign: ".to_owned() + &hex::encode(&sign)));
            info!(&("eth_addr: ".to_owned() + &hex::encode(&eth_addr)));
         
            let secp_instruction = make_secp256k1_instruction(message, sign, eth_addr);
            invoke(&secp_instruction, accounts)?;

            info!("call done");

            for index in vec![0, 1, 2, 3, 4, 5] {
                info!(&("index: ".to_owned() + &index.to_string()));  

                match load_instruction_at(index, &sysvara_account.try_borrow_data()?) {
                    Ok(instr) => {
                        info!(&format!("ID: {}", instr.program_id));
                        info!(&("INSTRUCTION: ".to_owned() + &hex::encode(&instr.data)));            
                    },
                    Err(err) => {
                        info!("ERR");
                    }
                }                
            }

            Ok(())
        },
    };

/*    let result = if program_lamports == 0 {
        do_create_account(program_id, accounts, instruction_data)
    } else {
        let account_type = {program_info.data.borrow()[0]};
        if account_type == 0 {
            let instruction: LoaderInstruction = limited_deserialize(instruction_data)
                .map_err(|_| ProgramError::InvalidInstructionData)?;

            match instruction {
                LoaderInstruction::Write {offset, bytes} => {
                    do_write(program_info, offset, &bytes)
                },
                LoaderInstruction::Finalize => {
                    info!("FinalizeInstruction");
                    do_finalize(program_id, accounts, program_info)
                },
            }
        } else {
            info!("Execute");
            do_execute(program_id, accounts, instruction_data)
        }
    };*/

    info!(&("Total memory occupied: ".to_owned() + &BumpAllocator::occupied().to_string()));
    result
}

fn print_data(src: &[u8]) {    
    info!(&("data: ".to_owned() + &hex::encode(&src)));      
}

fn to_hex_string(bytes:& Vec<u8>) -> String {
    let strs: Vec<String> = bytes.iter().map(|b| format!("{:02X}", b)).collect();
    strs.connect("")
}

// entrypoint!(process_instruction);
// fn process_instruction(
//     _program_id: &Pubkey,
//     accounts: &[AccountInfo],
//     instruction_data: &[u8],
// ) -> ProgramResult {
//     if instruction_data.is_empty() {
//         return Err(ProgramError::InvalidAccountData);
//     }

//     let secp_instruction_index = instruction_data[0];
//     let account_info_iter = &mut accounts.iter();
//     let instruction_accounts = next_account_info(account_info_iter)?;
//     assert_eq!(*instruction_accounts.key, instructions::id());
//     let data_len = instruction_accounts.try_borrow_data()?.len();
//     if data_len < 2 {
//         return Err(ProgramError::InvalidAccountData);
//     }

//     let instruction = instructions::load_instruction_at(
//         secp_instruction_index as usize,
//         &instruction_accounts.try_borrow_data()?,
//     )
//     .map_err(|_| ProgramError::InvalidAccountData)?;

//     let current_instruction =
//         instructions::load_current_index(&instruction_accounts.try_borrow_data()?);
//     let my_index = instruction_data[1] as u16;
//     assert_eq!(current_instruction, my_index);

//     msg!(&format!("id: {}", instruction.program_id));
//     msg!(&format!("data[0]: {}", instruction.data[0]));
//     msg!(&format!("index: {}", current_instruction));
//     Ok(())
// }