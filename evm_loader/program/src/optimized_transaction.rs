use primitive_types::{H160, U256};
use solana_sdk::program_error::ProgramError;
use std::convert::TryFrom;
use std::convert::TryInto;

enum RLPField<'a> {
    Data { data: &'a [u8] },
    List { list: Vec<RLPField<'a>> },
    Integer { value: u64 },
}

impl<'a> RLPField<'a> {
    fn unpack(input: &'a [u8]) -> Option<(Self, &'a [u8])> {
        let (&ch, rest) = input.split_first().unwrap();
        if ch <= 0x7F {
            let value = u64::try_from(ch).unwrap();
            return Some((RLPField::Integer { value }, rest));
        } else if ch == 0x80 {
            let value: u64 = 0;
            return Some((RLPField::Integer { value }, rest));
        } else if ch <= 0xB7 {
            let l = ch - 0x80;
            let (data, rest) = rest.split_at(l.try_into().unwrap());
            return Some((RLPField::Data { data }, rest));
        } else if ch <= 0xBF {
            let l_len = ch - 0xB7;
            let (data, rest) = rest.split_at(l_len.try_into().unwrap());
            let length = data.try_into().ok().map(u64::from_be_bytes).unwrap();
            let (data, rest) = rest.split_at(length.try_into().unwrap());
            return Some((RLPField::Data { data }, rest));
        } else if ch == 0xC0 {
            let list = vec![];
            return Some((RLPField::List { list }, rest));
        } else if ch <= 0xF7 {
            let l = ch - 0xC0;
            let mut list = vec![];
            let (data, rest) = rest.split_at(l.try_into().unwrap());
            let mut rest_data = data;
            while rest_data.len() > 0 {
                let (item, data) = RLPField::unpack(rest_data).unwrap();
                rest_data = data;
                list.push(item);
            }
            return Some((RLPField::List { list }, rest));
        } else {
            let l_len = ch - 0xF7;
            let (length, rest) = if l_len == 1 {
                let (&data, rest) = rest.split_first().unwrap();
                (u64::try_from(data).unwrap(), rest)
            } else {
                let (data, rest) = rest.split_at(l_len.try_into().unwrap());
                (data.try_into().ok().map(u64::from_be_bytes).unwrap(), rest)
            };
            let mut list = vec![];
            let (data, rest) = rest.split_at(length.try_into().unwrap());
            let mut rest_data = data;
            while rest_data.len() > 0 {
                let (item, data) = RLPField::unpack(rest_data).unwrap();
                rest_data = data;
                list.push(item);
            }
            return Some((RLPField::List { list }, rest));
        }
    }
}

pub fn get_data_opt<'a>(raw_tx: &'a [u8]) -> Option<(u64, H160, std::vec::Vec<u8>)> {
    let (lst, data) = RLPField::unpack(&raw_tx).unwrap();
    match lst {
        RLPField::List { list } => {
            let tx_nonce = match list[0] {
                RLPField::Integer { value } => value,
                _ => return None,
            };
            let tx_to = match list[3] {
                RLPField::Data { data } => H160::from_slice(data),
                _ => return None,
            };
            let tx_data = match list[5] {
                RLPField::Data { data } => data.to_vec(),
                _ => return None,
            };
            Some((tx_nonce, tx_to, tx_data))
        }
        _ => return None,
    }
}
