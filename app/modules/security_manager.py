import base64
import os
import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import pyotp

class SecurityManager:
    def __init__(self, secret_key: bytes = None):
        """
        Initialize SecurityManager.
        :param secret_key: A 32-byte key for AES-256 encryption. If None, a random key is generated.
        """
        self.secret_key = secret_key or os.urandom(32)

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypts an API key using AES-256-CBC.
        """
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.secret_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Padding to a multiple of 16 bytes
        pad_len = 16 - (len(api_key) % 16)
        padded_api_key = api_key + (chr(pad_len) * pad_len)
        
        ciphertext = encryptor.update(padded_api_key.encode('utf-8')) + encryptor.finalize()
        
        # Return base64 encoded string containing iv + ciphertext for easier storage
        return base64.b64encode(iv + ciphertext).decode('utf-8')

    def decrypt_api_key(self, encrypted_api_key_b64: str) -> str:
        """
        Decrypts an encrypted API key using AES-256-CBC.
        """
        data = base64.b64decode(encrypted_api_key_b64.encode('utf-8'))
        iv = data[:16]
        ciphertext = data[16:]
        
        cipher = Cipher(algorithms.AES(self.secret_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_api_key = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        pad_len = padded_api_key[-1]
        api_key = padded_api_key[:-pad_len].decode('utf-8')
        
        return api_key

    def generate_2fa_secret(self) -> str:
        """
        Generates a 2FA base32 secret.
        """
        return pyotp.random_base32()

    def get_2fa_uri(self, secret: str, account_name: str, issuer_name: str = "ElcoApp") -> str:
        """
        Generates a provisioning URI for Google Authenticator or similar apps.
        """
        return pyotp.totp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer_name)

    def verify_2fa_code(self, secret: str, code: str) -> bool:
        """
        Verifies a 2FA code against a secret.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    def create_database_backup_snapshot(self, db_connection_string: str, backup_dir: str) -> str:
        """
        Creates a database backup snapshot stub.
        In a real scenario, this would use a database dump tool (like pg_dump, mysqldump)
        and store the output in the backup_dir.
        """
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"db_backup_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Stub logic: just writing a dummy file
        try:
            with open(backup_path, 'w') as f:
                f.write(f"-- Database backup snapshot created at {timestamp}\n")
                f.write(f"-- Source: {db_connection_string}\n")
                f.write("-- (Backup data goes here)\n")
            return backup_path
        except Exception as e:
            raise Exception(f"Failed to create backup snapshot: {str(e)}")
