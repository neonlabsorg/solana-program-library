use std::borrow::Cow;
use serde::{Serialize, Deserialize};
use impl_serde::serialize as bytes;
use rlp::RlpStream;
use sha3::{Digest, Keccak256};

pub use ethereum_types::{Address, U256};

/// Hex-serialized shim for `Vec<u8>`.
#[derive(Serialize, Deserialize, Debug, Hash, PartialOrd, Ord, PartialEq, Eq, Clone, Default)]
pub struct Bytes(#[serde(with="bytes")] pub Vec<u8>);
impl From<Vec<u8>> for Bytes {
	fn from(s: Vec<u8>) -> Self { Bytes(s) }
}

impl std::ops::Deref for Bytes {
	type Target = [u8];
	fn deref(&self) -> &[u8] { &self.0[..] }
}

#[derive(Clone)]
pub struct Transaction {
    pub from: Address,
    pub to: Option<Address>,
    pub nonce: U256,
    pub gas: U256,
    pub gas_price: U256,
    pub value: U256,
    pub data: Bytes,
}

#[derive(Clone)]
pub struct SignedTransaction<'a> {
    pub transaction: Cow<'a, Transaction>,
    pub v: u64,
    pub r: U256,
    pub s: U256,
}

mod replay_protection {
	/// Adds chain id into v
	pub fn add(v: u8, chain_id: u64) -> u64 {
		v as u64 + 35 + chain_id * 2
	}

	/// Extracts chain_id from v
	pub fn chain_id(v: u64) -> Option<u64> {
		match v {
			v if v >= 35 => Some((v - 35) / 2),
			_ => None
		}
	}
}

impl<'a> SignedTransaction<'a> {
    pub fn new(
        transaction: Cow<'a, Transaction>,
        chain_id: u64,
        v: u8,
        r: [u8; 32],
        s: [u8; 32],
    ) -> Self {
        let v = replay_protection::add(v, chain_id);
        let r = U256::from_big_endian(&r);
        let s = U256::from_big_endian(&s);

        Self {
            transaction,
            v,
            r,
            s,
        }
    }
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
        s.append(&self.data.0);
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
		s.append(&self.transaction.data.0);
        s.append(&self.v);
        s.append(&self.r);
        s.append(&self.s);
    }
}

//let data = vec![0x83, b'c', b'a', b't'];
//let decoded: SignedTransaction = rlp::decode(&data).unwrap();

pub fn get_tx_sender(tx: &SignedTransaction) -> Address { // TODO: Should return Result and should return error if error
    if tx.r == U256::zero() {
        return Address::from([0xffu8; 20]);
    }
    if tx.v == 27u32.into() || tx.v == 28u32.into() {
        let vee = tx.v.clone();
        let rlp_data = rlp::encode(tx.transaction.as_ref());
        let sig_hash = Keccak256::digest(&rlp_data);

        // TODO construct compact and recover pubkey
    } else if tx.v >= 37u32.into() {
        // TODO
    } else {
        return Address::from([0xffu8; 20]);
    }
    return Address::from([0xffu8; 20]);
}