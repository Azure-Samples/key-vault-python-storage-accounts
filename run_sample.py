import sys
from util import SampleConfig
from storage_account_sample import StorageAccountSample
from sas_definition_sample import SasDefinitionSample


def run_all_samples():

    config = SampleConfig()
    sa_sample = StorageAccountSample(config=config)
    sas_sample = SasDefinitionSample(config=config)

    sa_sample.add_storage_account()
    sa_sample.update_storage_account()
    sa_sample.regenerate_storage_account_key()
    sa_sample.get_storage_accounts()
    sas_sample.create_account_sas_definition()
    sas_sample.create_blob_sas_defintion()
    sas_sample.get_sas_definitions()
    sa_sample.delete_storage_account()


if __name__ == "__main__":
    run_all_samples()
