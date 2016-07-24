"""Console application for Trustery."""

import atexit
import binascii
import logging
import time

import click

from trustery.consoleutil import echo_attribute_block
from trustery.events import Events
from trustery.transactions import Transactions
from trustery import rsakeys, userconfig

from Crypto.PublicKey import RSA


class StrParamType(click.ParamType):
    """Click parameter type that converts data using str()."""
    name = 'STR'

    def convert(self, value, param, ctx):
        return str(value)

STR = StrParamType()


def _addblindedrsa(fingerprint, signingattributeid, ipfs=False):
    key = userconfig.load_rsa_key(fingerprint)

    events = Events()
    signingattribute = events.retrieve_attribute(signingattributeid)
    signingkey = RSA.importKey(signingattribute['data'])

    blindedkey, r = rsakeys.generate_blinded_key_data(key, signingkey)

    userconfig.add_rsa_blinded_key_data(blindedkey, r)

    transactions = Transactions()

    if ipfs:
        transactions.add_blinded_attribute_over_ipfs('rsakey', signingattributeid, blindedkey)
    else:
        transactions.add_blinded_attribute_with_hash('rsakey', signingattributeid, blindedkey)

    click.echo()
    click.echo("Transaction sent.")


def _signblindedrsa(blindedattributeid, ipfs=False):
    click.echo()

    events = Events()
    try:
        blindedattribute = events.retrieve_blinded_attribute(blindedAttributeID=blindedattributeid)
    except IndexError:
        click.echo("Error: No such attribute.")
        return

    signingattribute = events.filter_attributes(attributeID=blindedattribute['signingAttributeID'])[0]
    hexfingerprint = binascii.hexlify(signingattribute['identifier'])

    try:
        signingkey = userconfig.load_rsa_key(hexfingerprint)
    except KeyError:
        click.echo("Error: You do not have the private key for the target signing key of this blinded attribute.")
        return

    signature = rsakeys.sign_blinded_key(blindedattribute['data'], signingkey)

    transactions = Transactions()
    if ipfs:
        transactions.sign_blinded_attribute_over_ipfs(blindedattributeid, signature)
    else:
        transactions.sign_blinded_attribute_with_hash(blindedattributeid, signature)

    click.echo("Transaction sent.")


@click.group()
def cli():
    """Ethereum-based identity system."""
    # Prevent the requests module from printing INFO logs to the console.
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Save the configuration on exit.
    atexit.register(userconfig.config.write)


@cli.command()
@click.option('--attributetype', prompt=True, type=STR)
@click.option('--has_proof', prompt=True, type=bool)
@click.option('--identifier', prompt=True, type=STR)
@click.option('--data', prompt=True, type=STR)
@click.option('--datahash', prompt=True, type=STR)
def rawaddattribute(attributetype, has_proof, identifier, data, datahash):
    """(Advanced) Manually add an attribute to your identity."""
    transactions = Transactions()
    transactions.add_attribute(attributetype, has_proof, identifier, data, datahash)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--attributeid', prompt=True, type=int)
@click.option('--expiry', prompt=True, type=STR)
def rawsignattribute(attributeid, expiry):
    """(Advanced) Manually sign an attribute about an identity."""
    transactions = Transactions()
    transactions.sign_attribute(attributeid, expiry)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--signatureid', prompt=True, type=STR)
def rawrevokeattribute(signatureid):
    """(Advanced) Manaully revoke your signature of an attribute."""
    transactions = Transactions()
    transactions.revoke_signature(signatureid)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--attributetype', prompt='Attribute type', help='Attribute type', type=STR)
@click.option('--identifier', prompt='Attribute identifier', help='Attribute identifier', type=STR)
@click.option('--data', prompt='Attribute data', default='', help='Attribute data', type=STR)
def add(attributetype, identifier, data):
    """Add an attribute to your identity."""
    transactions = Transactions()
    transactions.add_attribute_with_hash(attributetype, False, identifier, data)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--attributetype', prompt='Attribute type', help='Attribute type', type=STR)
@click.option('--identifier', prompt='Attribute identifier', help='Attribute identifier', type=STR)
@click.option('--data', prompt='Attribute data', default='', help='Attribute data', type=unicode)
def ipfsadd(attributetype, identifier, data):
    """Add an attribute to your identity over IPFS."""
    transactions = Transactions()
    transactions.add_attribute_over_ipfs(attributetype, False, identifier, data)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--attributeid', prompt='Attribute ID', help='Attribute ID', type=int)
@click.option('--expires', prompt='Signature days to expire', default=365, help='Signature days to expire', type=int)
def sign(attributeid, expires):
    """Sign an attribute."""
    transactions = Transactions()

    expiry = int(time.time()) + expires * 60 * 60 * 24
    transactions.sign_attribute(attributeid, expiry)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--blindedattributeid', prompt='Blinded attribute ID', help='Blinded attribute ID', type=int)
def signblindedrsa(blindedattributeid):
    """Sign a blinded RSA attribute."""
    _signblindedrsa(blindedattributeid)


@cli.command()
@click.option('--blindedattributeid', prompt='Blinded attribute ID', help='Blinded attribute ID', type=int)
def ipfssignblindedrsa(blindedattributeid):
    """Sign a blinded RSA attribute over IPFS."""
    _signblindedrsa(blindedattributeid, ipfs=True)


@cli.command()
@click.option('--signatureid', prompt='Signature ID', help='Signature ID', type=int)
def revoke(signatureid):
    """Revoke one of your signatures."""
    transactions = Transactions()
    transactions.revoke_signature(signatureid)

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--address', prompt='Ethereum address', help='Ethereum address', type=STR)
def trust(address):
    """Trust an Ethereum address."""
    click.echo()

    if userconfig.is_trusted(address):
        click.echo("Address " + address + " is already trusted.")
    else:
        userconfig.trust(address)
        click.echo("Address " + address + " trusted.")


@cli.command()
@click.option('--address', prompt='Ethereum address', help='Ethereum address', type=STR)
def untrust(address):
    """Untrust an Ethereum address."""
    click.echo()

    if not userconfig.is_trusted(address):
        click.echo("Address " + address + " is already not trusted.")
    else:
        userconfig.untrust(address)
        click.echo("Address " + address + " untrusted.")


@cli.command()
def trusted():
    """View the list of trusted Ethereum addresses."""
    for address in userconfig.get_trusted():
        click.echo(address)


@cli.command()
@click.option('--attributeid', prompt='Attribute ID', help='Attribute ID', type=int)
def retrieve(attributeid):
    """Retrieve an attribute."""
    events = Events()
    attribute = events.retrieve_attribute(attributeid)

    if attribute is None:
        click.echo("No such attribute.")
        return

    click.echo()

    echo_attribute_block(attribute)
    click.echo()

    if 'proof_valid' in attribute:
        click.echo("Proof status for attribute ID #" + str(attribute['attributeID']) + ':')
        if attribute['proof_valid'] is None:
            click.echo("\tUnknown")
        elif attribute['proof_valid']:
            click.echo("\tValid")
        else:
            click.echo("\tINVALID")

        click.echo()

    click.echo("Signatures for attribute ID #" + str(attribute['attributeID']) + ':')
    for signature in attribute['signatures_status']['signatures']:
        sig_line = "\t#" + str(signature['signatureID'])

        if signature['revocation']:
            sig_line += " [revoked]"
        elif signature['expired']:
            sig_line += " [expired]"
        elif signature['valid']:
            sig_line += " [valid]"

        sig_line += " by " + signature['signer']
        sig_line += (" [trusted]" if userconfig.is_trusted(attribute['owner']) else " [untrusted]")
        click.echo(sig_line)

    click.echo()
    click.echo("--ATTRIBUTE DATA:")
    click.echo(attribute['data'])


@cli.command()
@click.option('--blindedattributeid', prompt='Blinded attribute ID', help='Blinded attribute ID', type=int)
def retrieveblinded(blindedattributeid):
    """Retrieve a blinded attribute."""
    events = Events()
    attribute = events.retrieve_blinded_attribute(blindedattributeid)

    if attribute is None:
        click.echo("No such attribute.")
        return

    click.echo()

    echo_attribute_block(attribute)
    click.echo()

    click.echo("Blind signatures for blinded attribute ID #" + str(attribute['blindedAttributeID']) + ':')
    for signature in events.filter_blind_signatures(blindedAttributeID=blindedattributeid):
        sig_line = "\t#" + str(signature['blindSignatureID'])

        sig_line += " by " + signature['signer']
        sig_line += (" [trusted]" if userconfig.is_trusted(attribute['owner']) else " [untrusted]")
        click.echo(sig_line)

    click.echo()
    click.echo("--ATTRIBUTE DATA:")
    click.echo(attribute['data'])


@cli.command()
@click.option('--attributetype', help='Attribute type', type=STR)
@click.option('--identifier', help='Attribute identifier', type=STR)
@click.option('--owner', help='Attribute owner', type=STR)
def search(attributetype, identifier, owner):
    """Search for attributes."""
    # Pad identifiers with zeros.
    if identifier is not None:
        if identifier.startswith('0x'): # Hex data.
            identifier = identifier.ljust(66, '0')
        else:
            identifier = identifier.ljust(32, '\x00')

    events = Events()
    attributes = events.filter_attributes(None, owner, identifier)

    for attribute in attributes:
        if attributetype is not None and attributetype != attribute['attributeType']:
            continue

        signatures_status = events.get_attribute_signatures_status(attribute['attributeID'])

        echo_attribute_block(attribute, signatures_status)
        click.echo()


@cli.command()
@click.option('--attributetype', help='Attribute type', type=STR)
@click.option('--owner', help='Attribute owner', type=STR)
def searchblinded(attributetype, owner):
    """Search for blinded attributes."""
    events = Events()
    attributes = events.filter_blinded_attributes(None, owner)

    for attribute in attributes:
        if attributetype is not None and attributetype != attribute['attributeType']:
            continue

        signatures = len(events.filter_blind_signatures(blindedAttributeID=attribute['blindedAttributeID']))

        echo_attribute_block(attribute)
        click.echo("\t[" + str(signatures) + " blind signature" + ("]" if signatures == 1 else "s]"))
        click.echo()


@cli.command()
@click.option('--keyid', prompt='Key ID', help='Key ID', type=STR)
def ipfsaddpgp(keyid):
    """Add a PGP key attribute to your identity over IPFS."""
    transactions = Transactions()
    click.echo()

    try:
        transactions.add_pgp_attribute_over_ipfs(keyid)
    except ValueError as e:
        click.echo("Error: " + e.message)
        return

    click.echo("Transaction sent.")


@cli.command()
def newrsa():
    """Create a new RSA key."""
    click.echo("Generating key...")
    keyfingerprint = userconfig.add_rsa_key(rsakeys.new_key())
    click.echo("Key generated with fingerprint: " + keyfingerprint)


@cli.command()
@click.option('--fingerprint', prompt='Key fingerprint', help='Key fingerprint', type=STR)
def addrsa(fingerprint):
    """Add an RSA key attribute to your identity."""
    rsakey = userconfig.load_rsa_key(fingerprint)

    transactions = Transactions()
    transactions.add_attribute_with_hash(
        attributetype='rsakey',
        has_proof=False,
        identifier=fingerprint.decode('hex'),
        data=rsakey.publickey().exportKey()
    )

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
@click.option('--fingerprint', prompt='Key fingerprint', help='Key fingerprint', type=STR)
def ipfsaddrsa(fingerprint):
    """Add an RSA key attribute to your identity over IPFS."""
    rsakey = userconfig.load_rsa_key(fingerprint)

    transactions = Transactions()
    transactions.add_attribute_over_ipfs(
        attributetype='rsakey',
        has_proof=False,
        identifier=fingerprint.decode('hex'),
        data=rsakey.publickey().exportKey()
    )

    click.echo()
    click.echo("Transaction sent.")


@cli.command()
def listrsa():
    """View the list of fingerprints of stored RSA keys."""
    for fingerprint in userconfig.get_rsa_fingerprints():
        click.echo(fingerprint)


@cli.command()
@click.option('--fingerprint', prompt='Key fingerprint', help='Key fingerprint', type=STR)
@click.option('--signingattributeid', prompt='ID of the attribute that will sign the key', help='ID of the attribute that will sign the key', type=int)
def addblindedrsa(fingerprint, signingattributeid):
    """Add a blinded RSA attribute to your identity."""
    _addblindedrsa(fingerprint, signingattributeid)


@cli.command()
@click.option('--fingerprint', prompt='Key fingerprint', help='Key fingerprint', type=STR)
@click.option('--signingattributeid', prompt='ID of the attribute that will sign the key', help='ID of the attribute that will sign the key', type=int)
def ipfsaddblindedrsa(fingerprint, signingattributeid):
    """Add a blinded RSA attribute to your identity over IPFS."""
    _addblindedrsa(fingerprint, signingattributeid, ipfs=True)


@cli.command()
@click.option('--blindsignatureid', prompt='Blind signature ID', help='Blind signature ID', type=int)
def unblindrsa(blindsignatureid):
    """Unblind a blinded RSA signature."""
    click.echo()

    events = Events()
    try:
        signature = events.retrieve_blind_signature(blindsignatureid)
    except IndexError:
        click.echo("Error: No such signature.")
        return

    attribute = events.retrieve_blinded_attribute(signature['blindedAttributeID'])
    signingattribute = events.retrieve_attribute(attribute['signingAttributeID'])
    signingkey = RSA.importKey(signingattribute['data'])

    try:
        blindingfactor = userconfig.get_rsa_blinding_factor(attribute['data'])
    except KeyError:
        click.echo("Error: You do not have the blinding factor for this signature.")
        return

    unblindedsignature = rsakeys.unblind_signature(signature['data'], blindingfactor, signingkey)
    click.echo("Unblinded signature: " + unblindedsignature)
