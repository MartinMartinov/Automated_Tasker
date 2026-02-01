from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import base64
import json
from pathlib import Path
import random
from getpass import getpass

vault_password = getpass("Vault password: ")

class Vault:
    """A class for storing various sensitive pieces of data encrypted with a provided password."""

    def __init__(self, file_name="entries.json"):
        self.password = vault_password
        self.file_path = self.get_vault_directory() / file_name

    @staticmethod
    def get_vault_directory() -> Path:
        """Get (and create if it doesn't exists) the directory for the vault file.

        Returns:
            Path: The Path of the directory
        """
        home_directory = Path.home()
        vault_directory = home_directory / "vault"
        vault_directory.mkdir(exist_ok=True)
        return vault_directory

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Create a key using PBKDF2HMAC.

        Parameters:
            password (str): The password string
            salt (bytes): A random salt

        Returns:
            bytes: The derived key
        """
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        return kdf.derive(password.encode())

    @staticmethod
    def generate_random_bytes(size: int) -> bytes:
        """Create random bytes using random.randint

        Parameters:
            size (int): The number of bytes

        Returns:
            bytes: The random bytes of len size
        """
        return bytes([random.randint(0, 255) for _ in range(size)])

    def encrypt_data(self, data: bytes) -> bytes:
        """The actual encryption function using AESGCM.

        Parameters:
            data (bytes): The plaintext entry

        Returns:
            bytes: The ciphertext entry
        """
        salt = self.generate_random_bytes(16)
        key = self.derive_key(self.password, salt)
        aesgcm = AESGCM(key)
        nonce = self.generate_random_bytes(12)
        encrypted_data = aesgcm.encrypt(nonce, data.encode(), None)
        return base64.b64encode(salt + nonce + encrypted_data).decode()

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """The actual decryption function using AESGCM.

        Parameters:
            encrypted_data (bytes): The ciphertext entry

        Returns:
            bytes: The plaintext entry
        """
        encrypted_data = base64.b64decode(encrypted_data)
        salt = encrypted_data[:16]
        nonce = encrypted_data[16:28]
        ciphertext = encrypted_data[28:]
        key = self.derive_key(self.password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()

    def store_entry(self, tag: str, entry: str) -> None:
        """The function that takes a tag and entry, encrypts the entry, and stores it at location tag.

        Parameters:
            tag (str): The lookup value for the entry
            entry (str): The plaintext for the entry
        """
        try:
            with open(self.file_path, "r") as file:
                entries = json.load(file)
        except FileNotFoundError:
            entries = {}

        encrypted_entry = self.encrypt_data(entry)
        entries[tag] = encrypted_entry

        with open(self.file_path, "w") as file:
            json.dump(entries, file)

    def delete_entry(self, tag: str) -> None:
        """The function that deletes the entry at location tag.

        Parameters:
            tag (str): The lookup value for the entry
        """
        try:
            with open(self.file_path, "r") as file:
                entries = json.load(file)
        except FileNotFoundError:
            entries = {}

        entries.pop(tag)

        with open(self.file_path, "w") as file:
            json.dump(entries, file)

    def load_entries(self) -> dict[str, bytes]:
        """Load (and decrypt) all the entries in the vault.

        Returns:
            dict[str,bytes]: A dict mapping tags to entries
        """
        try:
            with open(self.file_path, "r") as file:
                entries = json.load(file)
        except FileNotFoundError:
            return {}

        decrypted_entries = {}
        for tag, encrypted_entry in entries.items():
            try:
                decrypted_entry = self.decrypt_data(encrypted_entry)
                decrypted_entries[tag] = decrypted_entry
            except Exception as e:
                print(f"Error decrypting entry for tag '{tag}': {e}")
                raise e

        return decrypted_entries

vault = Vault()