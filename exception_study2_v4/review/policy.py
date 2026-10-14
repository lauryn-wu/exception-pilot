"""Identical judge rubrics/schemas/routing with an explicit v4 source contract."""
import copy
from exception_pilot.core import digest
from exception_review.policy import (DETECTION,EDIT,VERIFY,UNTRUSTED,ARMS,CRITERIA,DETECT_SCHEMA,
    DRAFT_SCHEMA,VERIFY_SCHEMA,SCHEMAS,RUBRICS,RULES,schema_check,freeze_policy as legacy_policy)
from ..core import source_hash as code_hash
from .. import PROTOCOL

def freeze_policy(config):
    value=copy.deepcopy(legacy_policy(config))
    value.pop('policy_hash')
    value.update(source_contract=PROTOCOL,code_hash=code_hash())
    value['policy_hash']=digest(value)
    return value
