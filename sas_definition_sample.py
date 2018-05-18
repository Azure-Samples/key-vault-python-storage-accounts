# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# This script expects that the following environment vars are set
#
# AZURE_TENANT_ID: with your Azure Active Directory tenant id or domain
# AZURE_CLIENT_ID: with your Azure Active Directory Service Principal AppId
# AZURE_CLIENT_SECRET: with your Azure Active Directory Application Key
# AZURE_SUBSCRIPTION_ID: with your Azure Subscription Id
#

import uuid
from util import KeyVaultSampleBase, keyvaultsample


class SasDefinitionSample(KeyVaultSampleBase):
    """
    A collection of samples that demonstrate authenticating with the KeyVaultClient and KeyVaultManagementClient
    """
    def __init__(self, config=None):
        from azure.keyvault import KeyVaultClient, KeyVaultAuthentication, AccessToken
        from msrestazure.azure_active_directory import ServicePrincipalCredentials

        super(SasDefinitionSample, self).__init__(config=config)

        self.keyvault_client = KeyVaultClient(ServicePrincipalCredentials(client_id=self.config.client_id,
                                                                          secret=self.config.client_secret,
                                                                          tenant=self.config.tenant_id))

    def run_all_samples(self):
        self.create_account_sas_definition()
        self.create_blob_sas_defintion()
        self.get_sas_definitions()

    @keyvaultsample
    def create_account_sas_definition(self):
        """
        Creates an account sas definition, to manage storage account and its entities.
        """
        from azure.storage.common import SharedAccessSignature, CloudStorageAccount
        from azure.keyvault.models import SasTokenType, SasDefinitionAttributes
        from azure.keyvault import SecretId

        # To create an account sas definition in the vault we must first create the template. The
        # template_uri for an account sas definition is the intended account sas token signed with an arbitrary key.
        # Use the SharedAccessSignature class from azure.storage.common to create a account sas token
        sas = SharedAccessSignature(account_name=self.config.storage_account_name,
                                    # don't sign the template with the storage account key use key 00000000
                                    account_key='00000000')
        account_sas_template = sas.generate_account(services='bfqt',  # all services blob, file, queue and table
                                                    resource_types='sco',  # all resources service, template, object
                                                    permission='acdlpruw',
                                                    # all permissions add, create, list, process, read, update, write
                                                    expiry='2020-01-01')  # expiry will be ignored and validity period will determine token expiry

        # use the created template to create a sas definition in the vault
        attributes = SasDefinitionAttributes(enabled=True)
        sas_def = self.keyvault_client.set_sas_definition(vault_base_url=self.sample_vault_url,
                                                          storage_account_name=self.config.storage_account_name,
                                                          sas_definition_name='acctall',
                                                          template_uri=account_sas_template,
                                                          sas_type=SasTokenType.account,
                                                          validity_period='PT2H',
                                                          sas_definition_attributes=attributes)

        # When the sas definition is created a corresponding managed secret is also created in the vault, the. This
        # secret is used to provision sas tokens according to the sas definition.  Users retrieve the sas token
        # via the get_secret method.

        # get the secret id from the returned SasDefinitionBundle
        sas_secret_id = SecretId(uri=sas_def.secret_id)
        # call get_secret and the value of the returned SecretBundle will be a newly issued sas token
        acct_sas_token = self.keyvault_client.get_secret(vault_base_url=sas_secret_id.vault,
                                                         secret_name=sas_secret_id.name,
                                                         secret_version=sas_secret_id.version).value

        # create the cloud storage account object
        cloud_storage_account = CloudStorageAccount(account_name=self.config.storage_account_name,
                                                    sas_token=acct_sas_token)

        # create a blob with the account sas token
        blob_service = cloud_storage_account.create_block_blob_service()
        blob_service.create_container('blobcontainer')
        blob_service.create_blob_from_text(container_name='blobcontainer',
                                           blob_name='blob1',
                                           text=u'test blob1 data')

    @keyvaultsample
    def create_blob_sas_defintion(self):
        """
        Creates a service SAS definition with access to a blob container.
        """

        from azure.storage.blob import BlockBlobService, ContainerPermissions
        from azure.keyvault.models import SasTokenType, SasDefinitionAttributes
        from azure.keyvault import SecretId

        # create the blob sas definition template
        # the sas template uri for service sas definitions contains the storage entity url with the template token
        # this sample demonstrates constructing the template uri for a blob container, but a similar approach can
        # be used for all other storage service, i.e. File, Queue, Table

        # create a template sas token for the container
        service = BlockBlobService(account_name=self.config.storage_account_name,
                                   # don't sign the template with the storage account key use key 00000000
                                   account_key='00000000')
        permissions = ContainerPermissions(read=True, write=True, delete=True, list=True)
        temp_token = service.generate_container_shared_access_signature(container_name='blobcontainer',
                                                                        permission=permissions,
                                                                        expiry='2020-01-01')

        # use the BlockBlobService to construct the template uri for the container sas definition
        blob_sas_template_uri = service.make_container_url(container_name='blobcontainer',
                                                           protocol='https',
                                                           sas_token=temp_token)
        # create the sas definition in the vault
        attributes = SasDefinitionAttributes(enabled=True)
        blob_sas_def = self.keyvault_client.set_sas_definition(vault_base_url=self.sample_vault_url,
                                                               storage_account_name=self.config.storage_account_name,
                                                               sas_definition_name='blobcontall',
                                                               template_uri=blob_sas_template_uri,
                                                               sas_type=SasTokenType.service,
                                                               validity_period='PT2H',
                                                               sas_definition_attributes=attributes)

        # use the sas definition to provision a sas token and use it to  create a BlockBlobClient
        # which can interact with blobs in the container

        # get the secret_id of the container sas definition and get the token from the vault as a secret
        sas_secret_id = SecretId(uri=blob_sas_def.secret_id)
        blob_sas_token = self.keyvault_client.get_secret(vault_base_url=sas_secret_id.vault,
                                                         secret_name=sas_secret_id.name,
                                                         secret_version=sas_secret_id.version).value
        service = BlockBlobService(account_name=self.config.storage_account_name,
                                   sas_token=blob_sas_token)
        service.create_blob_from_text(container_name='blobcontainer',
                                      blob_name='blob2',
                                      text=u'test blob2 data')
        blobs = list(service.list_blobs(container_name='blobcontainer'))

        for blob in blobs:
            service.delete_blob(container_name='blobcontainer',
                                blob_name=blob.name)

    @keyvaultsample
    def get_sas_definitions(self):
        """
        List the sas definitions for the storage account, and get each.
        """
        from azure.keyvault import StorageSasDefinitionId

        # list the sas definitions for the storage account
        print('list and get sas definitions for the managed storage account')
        sas_defs = list(self.keyvault_client.get_sas_definitions(vault_base_url=self.sample_vault_url,
                                                                 storage_account_name=self.config.storage_account_name,
                                                                 maxresults=5))

        # for each sas definition parse the id and get the SasDefinitionBundle
        for s in sas_defs:
            sas_def_id = StorageSasDefinitionId(uri=s.id)
            sas_def = self.keyvault_client.get_sas_definition(vault_base_url=sas_def_id.vault,
                                                              storage_account_name=sas_def_id.account_name,
                                                              sas_definition_name=sas_def_id.sas_definition)
            print(sas_def_id.sas_definition, sas_def.template_uri)


if __name__ == "__main__":
    SasDefinitionSample().run_all_samples()