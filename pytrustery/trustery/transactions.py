"""API for making Trustery tranactions."""

import io

from ethereum import abi

from ipfsapi import ipfsclient
from gpgapi import generate_pgp_attribute_data
from ethapi import TRUSTERY_ABI
from ethapi import TRUSTERY_DEFAULT_ADDRESS
from ethapi import ethclient
from ethapi import encode_api_data


class Transactions(object):
    """API for making Trustery tranactions."""
    def __init__(self, from_address=None, to_address=TRUSTERY_DEFAULT_ADDRESS):
        """
        Initialise transactions.

        from_address: the Ethereum address transactions should be sent from.
        to_address: the Ethereum Trustery contract address.
        """
        if from_address is None:
            # Use the first Ethereum account address if no from address is specified.
            self.from_address = ethclient.get_accounts()[0]
        else:
            self.from_address = from_address
        self.to_address = to_address

        # Initialise contract ABI.
        self._contracttranslator = abi.ContractTranslator(TRUSTERY_ABI)

    def _send_transaction(self, data):
        """
        Send a transaction.

        data: the transactions data.
        """
        return ethclient.send_transaction(
            _from=self.from_address,
            to=self.to_address,
            data=encode_api_data(data),
            gas=2000000, # TODO deal with gas limit more sensibly
        )

    def add_attribute(self, attributetype, has_proof, identifier, data, datahash):
        """
        Send a transaction to add an identity attribute.

        attributetype: the type of address.
        has_proof: True if the attribute has a cryptographic proof, otherwise False.
        identifier: the indexable identifier of the attribute.
        data: the data of the attribute.
        datahash: the Keccak hash of the data of the attribute if it is stored off-blockchain.
        """
        args = [attributetype, has_proof, identifier, data, datahash]
        data = self._contracttranslator.encode('addAttribute', args)
        return self._send_transaction(data)

    def add_attribute_with_hash(self, attributetype, has_proof, identifier, data):
        """
        Send a transaction to add an identity attribute, automatically calculating its datahash if the data is stored remotely.

        attributetype: the type of address.
        has_proof: True if the attribute has a cryptographic proof, otherwise False.
        identifier: the indexable identifier of the attribute.
        data: the data of the attribute.
        """
        datahash = '' # TODO calculate hash for remotely stored data
        return self.add_attribute(attributetype, has_proof, identifier, data, datahash)

    def add_attribute_over_ipfs(self, attributetype, has_proof, identifier, data):
        """
        Send a transaction to add an identity attribute, storing the data on IPFS first.

        attributetype: the type of attribute.
        has_proof: True if the attribute has a cryptographic proof, otherwise False.
        identifier: the indexable identifier of the attribute.
        data: the data of the attribute.
        """
        #  Store the data as an IPFS block and get its key.
        ipfs_key = ipfsclient.block_put(io.StringIO(unicode(data)))['Key']

        # Generate Trustery-specific URI for the IPFS block.
        ipfs_uri = 'ipfs-block://' + ipfs_key

        # Add the attribute.
        self.add_attribute(attributetype, has_proof, identifier, ipfs_uri, datahash='')

    def add_blinded_attribute(self, attributeType, signingAttributeID, data, datahash):
        """
        Send a transaction to add a blinded key attribute.

        attributetype: the type of attribute.
        signingAttributeID: the ID of the attribute that will sign this attribute.
        data: the blinded data of the attribute.
        datahash: the Keccak hash of the data of the attribute if it is stored off-blockchain.
        """
        args = [attributeType, signingAttributeID, data, datahash]
        data = self._contracttranslator.encode('addBlindedAttribute', args)
        return self._send_transaction(data)

    def add_blinded_attribute_with_hash(self, attributeType, signingAttributeID, data):
        """
        Send a transaction to add a blinded key attribute, automatically calculating its datahash if the data is stored remotely.

        attributetype: the type of attribute.
        signingAttributeID: the ID of the attribute that will sign this attribute.
        data: the blinded data of the attribute.
        """
        datahash = '' # TODO calculate hash for remotely stored data
        return self.add_blinded_attribute(attributeType, signingAttributeID, data, datahash)

    def add_blinded_attribute_over_ipfs(self, attributeType, signingAttributeID, data):
        """
        Send a transaction to add a blinded key attribute, storing the data on IPFS first.

        attributetype: the type of attribute.
        signingAttributeID: the ID of the attribute that will sign this attribute.
        data: the blinded data of the attribute.
        datahash: the Keccak hash of the data of the attribute if it is stored off-blockchain.
        """
        #  Store the data as an IPFS block and get its key.
        ipfs_key = ipfsclient.block_put(io.StringIO(unicode(data)))['Key']

        # Generate Trustery-specific URI for the IPFS block.
        ipfs_uri = 'ipfs-block://' + ipfs_key

        # Add the attribute.
        self.add_blinded_attribute(attributeType, signingAttributeID, ipfs_uri, datahash='')

    def add_pgp_attribute_over_ipfs(self, keyid):
        """
        Send a transaction to add an identity PGP attribute, storing the attribute data on IPFS.

        keyid: the ID of the PGP key.
        """
        # Generate PGP attribute data and get identifier (fingerprint).
        (fingerprint, data) = generate_pgp_attribute_data(keyid, self.from_address)

        # Express identifier as fingerprint in binary format.
        identifier = fingerprint.decode('hex')

        self.add_attribute_over_ipfs(
            attributetype='pgp-key',
            has_proof=True,
            identifier=identifier,
            data=data,
        )

    def sign_attribute(self, attributeID, expiry):
        """
        Send a transaction to sign an identity attribute.

        attributeID: the ID of the attribute.
        expiry: the expiry time of the attriute.
        """
        args = [attributeID, expiry]
        data = self._contracttranslator.encode('signAttribute', args)
        return self._send_transaction(data)

    def sign_blinded_attribute(self, blindedAttributeID, data, datahash):
        """
        Send a transaction to sign a blinded identity attribute.

        attributeID: the ID of the attribute.
        data: the data of the signature.
        datahash: the hash of the signature data if it is stored remotely.
        """
        args = [blindedAttributeID, data, datahash]
        data = self._contracttranslator.encode('signBlindedAttribute', args)
        return self._send_transaction(data)

    def sign_blinded_attribute_with_hash(self, blindedAttributeID, data):
        """
        Send a transaction to sign a blinded identity attribute, automatically calculating its datahash if the data is stored remotely.

        attributetype: the type of attribute.
        data: the data of the signature.
        """
        datahash = '' # TODO calculate hash for remotely stored data
        return self.sign_blinded_attribute(blindedAttributeID, data, datahash)

    def sign_blinded_attribute_over_ipfs(self, blindedAttributeID, data):
        """
        Send a transaction to sign a blinded identity attribute, storing the data on IPFS first.

        attributetype: the type of attribute.
        data: the data of the signature.
        """
        #  Store the data as an IPFS block and get its key.
        ipfs_key = ipfsclient.block_put(io.StringIO(unicode(data)))['Key']

        # Generate Trustery-specific URI for the IPFS block.
        ipfs_uri = 'ipfs-block://' + ipfs_key

        # Add the attribute signature.
        self.sign_blinded_attribute(blindedAttributeID, ipfs_uri, datahash='')

    def revoke_signature(self, signatureID):
        """
        Send a transaction to revoke a signature.

        signatureID: the ID of the signature.
        """
        args = [signatureID]
        data = self._contracttranslator.encode('revokeSignature', args)
        return self._send_transaction(data)
