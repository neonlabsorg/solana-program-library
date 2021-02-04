use std::borrow::Cow;
use rlp::RlpStream;

use solana_sdk::{
    entrypoint::ProgramResult,
    program_error::ProgramError,
    info,
};

use primitive_types::{H160, U256};

use secp256k1

pub fn check_tx(raw_tx: &[u8]) -> ProgramResult {
    let eth_tx: Result<SignedTransaction, _> = rlp::decode(&raw_tx);
    if eth_tx.is_err() {
        return Err(ProgramError::InvalidInstructionData);
    }
    let tx = eth_tx.unwrap();
    
    info!(&("       from: ".to_owned() + &tx.transaction.from.to_string()));
    info!(&("         to: ".to_owned() + &tx.transaction.to.unwrap().to_string()));
    info!(&("      nonce: ".to_owned() + &tx.transaction.nonce.to_string()));
    info!(&("        gas: ".to_owned() + &tx.transaction.gas.to_string()));
    info!(&("  gas_price: ".to_owned() + &tx.transaction.gas_price.to_string()));
    info!(&("      value: ".to_owned() + &tx.transaction.value.to_string()));
    info!(&("       data: ".to_owned() + &hex::encode(&tx.transaction.data)));
    info!(&("          v: ".to_owned() + &tx.v.to_string()));
    info!(&("          r: ".to_owned() + &tx.r.to_string()));
    info!(&("          s: ".to_owned() + &tx.s.to_string()));
    
    Err(ProgramError::InvalidInstructionData)
}

#[derive(Clone)]
pub struct Transaction {
    pub from: H160,
    pub to: Option<H160>,
    pub nonce: U256,
    pub gas: U256,
    pub gas_price: U256,
    pub value: U256,
    pub data: Vec<u8>,
}

#[derive(Clone)]
pub struct SignedTransaction<'a> {
    pub transaction: Cow<'a, Transaction>,
    pub v: u64,
    pub r: U256,
    pub s: U256,
}

fn debug(s: &str, err: rlp::DecoderError) -> rlp::DecoderError {
  // log::error!("Error decoding field: {}: {:?}", s, err);
    err
}

impl<'a> rlp::Decodable for SignedTransaction<'a> {
	fn decode(d: &rlp::Rlp) -> Result<Self, rlp::DecoderError> {
		if d.item_count()? != 9 {
			return Err(rlp::DecoderError::RlpIncorrectListLen);
		}

	    Ok(SignedTransaction {
			transaction: Cow::Owned(Transaction {
				nonce: d.val_at(0).map_err(|e| debug("nonce", e))?,
				gas_price: d.val_at(1).map_err(|e| debug("gas_price", e))?,
				gas: d.val_at(2).map_err(|e| debug("gas", e))?,
				to: {
                    let to = d.at(3).map_err(|e| debug("to", e))?;
                    if to.is_empty() {
                        if to.is_data() {
                            None
                        } else {
                            return Err(rlp::DecoderError::RlpExpectedToBeData)
                        }
                    } else {
                        Some(to.as_val().map_err(|e| debug("to", e))?)
                    }
                },
                from: Default::default(),
				value: d.val_at(4).map_err(|e| debug("value", e))?,
				data: d.val_at::<Vec<u8>>(5).map_err(|e| debug("data", e))?.into(),
			}),
			v: d.val_at(6).map_err(|e| debug("v", e))?,
			r: d.val_at(7).map_err(|e| debug("r", e))?,
			s: d.val_at(8).map_err(|e| debug("s", e))?,
		})
	}
}

impl rlp::Encodable for Transaction {
    fn rlp_append(&self, s: &mut RlpStream) {
        s.begin_list(6);
        s.append(&self.nonce);
        s.append(&self.gas_price);
        s.append(&self.gas);
        match self.to.as_ref() {
            None => s.append(&""),
            Some(addr) => s.append(addr),
        };
        s.append(&self.value);
        s.append(&self.data);
    }
}

impl<'a> rlp::Encodable for SignedTransaction<'a> {
	fn rlp_append(&self, s: &mut RlpStream) {
		s.begin_list(9);
		s.append(&self.transaction.nonce);
		s.append(&self.transaction.gas_price);
		s.append(&self.transaction.gas);
        match self.transaction.to.as_ref() {
            None => s.append(&""),
            Some(addr) => s.append(addr),
        };
		s.append(&self.transaction.value);
		s.append(&self.transaction.data);
        s.append(&self.v);
        s.append(&self.r);
        s.append(&self.s);
    }
}