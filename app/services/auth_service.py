from webauthn import (
    generate_registration_options, 
    verify_registration_response, 
    generate_authentication_options, 
    verify_authentication_response, 
    options_to_json, 
    base64url_to_bytes
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor, 
    AuthenticatorSelectionCriteria, 
    UserVerificationRequirement,
    ResidentKeyRequirement
)
from typing import List, Optional

class AuthService:
    def __init__(self, rp_id: str, rp_name: str, origin: str):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

    def generate_registration_options(self, user_id: str, user_name: str):
        return generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_id.encode(),
            user_name=user_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED
            )
        )

    def verify_registration_response(self, credential, challenge):
        return verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id
        )

    def generate_authentication_options(self, credential_ids: List[str] = []):
        creds = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(cid)) for cid in credential_ids]
        return generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=creds,
            user_verification=UserVerificationRequirement.PREFERRED
        )

    def verify_authentication_response(self, credential, challenge, public_key, sign_count):
        return verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            credential_public_key=base64url_to_bytes(public_key),
            credential_current_sign_count=sign_count
        )
    
    def options_to_json(self, options):
        return options_to_json(options)
    
    def bytes_to_base64url(self, b):
        return bytes_to_base64url(b)
