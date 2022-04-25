from pydantic import BaseModel, constr
from utils import global_util
from copy import deepcopy
import time


class UserSignup(BaseModel):
    emailOrPhone: constr(min_length=3)
    password: constr(min_length=6)
    medium: str = "email"

    def get_user_pk_sk(self):
        return {
            "PK": f"AUTH#{self.emailOrPhone}",
            "SK": f"AUTH#{self.emailOrPhone}"
        }


class ConfirmationCodeModel(BaseModel):
    userId: constr(min_length=3)
    code: constr(min_length=6, max_length=6)
    medium: constr(min_length=3)
    destination: constr(min_length=3)
    createdAt: int = None
    PK: str = ""
    SK: str = ""

    def __init__(self, **data: dict):
        super().__init__(**data)
        if self.createdAt is None:
            self.createdAt = int(time.time())
        CONFIRMATION_CODE = 'CONFIRMATION#CODE'
        USER_PREFIX = "#USER"

        self.PK = CONFIRMATION_CODE
        self.SK = f"{USER_PREFIX}#{self.userId}"

    def get_user_pk_sk(self):
        return {
            "PK": f"CONFIRMATION#CODE",
            "SK": f"#USER#{self.userId}"
        }

    # @validator('medium')
    # def check_medium(cls, medium):
    #     if medium not in constants.ALLOWED_REGISTRATION_MEDIUM:
    #         raise ValueError(f"Medium must be one of the following: {','.join(constants.ALLOWED_REGISTRATION_MEDIUM)}")
    #     return medium

    def as_dynamodb_json(self):
        item = {}
        attributes = deepcopy(vars(self))
        if '__initialised__' in attributes:
            del attributes['__initialised__']
        for attr_name, val in attributes.items():
            item[attr_name] = global_util.get_dynamodb_type_value(val)
        return item


class CodeValidityModel(BaseModel):
    emailOrPhone: constr(min_length=3)
    medium: str = ""
    confirmationCode: constr(min_length=6, max_length=6)

    # @root_validator
    # def check_medium(cls, values):
    #     medium = values.get('medium')
    #     if medium not in constants.ALLOWED_REGISTRATION_MEDIUM:
    #         raise ValueError(f"Medium must be one of the following: {','.join(constants.ALLOWED_REGISTRATION_MEDIUM)}")
    #     return values


class SigninModel(BaseModel):
    emailOrPhone: constr(min_length=3)
    medium: constr(min_length=3)
    password: constr(min_length=6)

    # @root_validator
    # def check_medium(cls, values):
    #     medium = values.get('medium')
    #     if medium not in ['phone', 'email']:
    #         raise ValueError(f"Medium must be one of the following: {','.join(constants.ALLOWED_REGISTRATION_MEDIUM)}")
    #     return values


class ExistingEmailPhoneModel(BaseModel):
    emailOrPhone: constr(min_length=3)
    medium: constr(min_length=3)
    userId: constr(min_length=3)
    PK: str = ""
    SK: str = ""
    createdAt: int = None

    def __init__(self, **data: dict):
        super().__init__(**data)
        if self.createdAt is None:
            self.createdAt = int(time.time())
        self.PK = global_util.EXISTING_EMAIL_PHONE
        self.SK = f"{self.emailOrPhone}"

    def get_user_pk_sk(self):
        return {
            "PK": f"{global_util.EXISTING_EMAIL_PHONE}",
            "SK": f"{self.emailOrPhone}"
        }

    def as_dynamodb_json(self):
        item = {}
        attributes = deepcopy(vars(self))
        if '__initialised__' in attributes:
            del attributes['__initialised__']
        for attr_name, val in attributes.items():
            item[attr_name] = global_util.get_dynamodb_type_value(val)
        return item


class LogoutModel(BaseModel):
    accessToken: constr(min_length=3)