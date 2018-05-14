# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# This script expects that the following environment vars are set, or they can be hardcoded in key_vault_sample_config, these values
# SHOULD NOT be hardcoded in any code derived from this sample:
#
# AZURE_TENANT_ID: with your Azure Active Directory tenant id or domain
# AZURE_CLIENT_ID: with your Azure Active Directory Service Principal AppId
# AZURE_CLIENT_OID: with your Azure Active Directory Service Principle Object ID
# AZURE_CLIENT_SECRET: with your Azure Active Directory Application Key
# AZURE_SUBSCRIPTION_ID: with your Azure Subscription Id
#
# These are read from the environment and exposed through the KeyVaultSampleConfig class. For more information please
# see the implementation in key_vault_sample_config.py

import uuid
from .key_vault_sample_base import KeyVaultSampleBase, keyvaultsample, run_all_samples, get_name


class StorageAccountSample(KeyVaultSampleBase):
    """
    A collection of samples that demonstrate authenticating with the KeyVaultClient and KeyVaultManagementClient
    """
    def __init__(self):
        from azure.keyvault import KeyVaultClient, KeyVaultAuthentication, AccessToken

        # certain methods in this sample

        # create a KeyVaultClient that authenticates as the user
        def authenticate_user(server, resource, scope, scheme):
            token = self.get_user_token(resource=resource)
            return AccessToken(scheme=token['tokenType'], token=token['accessToken'], key=None)

        keyvault_user_client = KeyVaultClient(KeyVaultAuthentication(authorization_callback=authenticate_user))

        self._user_id = None
        self._user_oid = None

    @keyvaultsample
    def add_storage_account(self):
        """
        Creates a storage account then adds the storage account to the vault to manage its keys.
        """
        from azure.mgmt.storage import StorageManagementClient
        from azure.mgmt.storage.models import StorageAccountCreateParameters, Sku, SkuName, Kind
        from msrestazure.azure_active_directory import AADTokenCredentials
        from azure.mgmt.authorization.models import RoleAssignmentCreateParameters
        from azure.keyvault.models import StorageAccountAttributes
        from azure.mgmt.keyvault.models import AccessPolicyEntry, Permissions, StoragePermissions

        self.storage_account_name = get_name('sa', '')

        # only user accounts with access to the storage account keys can add a storage account to
        # a vault.  For this reason this sample creates the storage account with a user account
        # authenticated through device login rather than the service principal credentials used
        # in other samples.

        # create the StorageManagementClient with user token credentials
        user_token_creds = AADTokenCredentials(self.get_user_token('https://management.core.windows.net/'))
        storage_mgmt_client = StorageManagementClient(user_token_creds, self.config.subscription_id)

        # create the storage account
        sa_params = StorageAccountCreateParameters(sku=Sku(SkuName.standard_ragrs),
                                                   kind=Kind.storage,
                                                   location=self.config.location)
        sa = storage_mgmt_client.storage_accounts.create(resource_group_name=self.config.group_name,
                                                         account_name=self.storage_account_name,
                                                         parameters=sa_params).result()

        # the KeyVault service must be given the "Storage Account Key Operator Service Role" on the
        # storage account before the storage account can be added to the vault

        # find the role definition for "Storage Account Key Operator Service Role"
        filter_str = 'roleName=Storage Account Key Operator Service Role'
        role_id = list(self.authorization_mgmt_client.role_definitions.list(scope='/', filter=filter_str))[0].id

        # create a role assignment granting the key vault service principal this role
        role_params = RoleAssignmentCreateParameters(role_definition_id=role_id,
                                                     # the Azure Key Vault service id
                                                     principal_id='cfa8b339-82a2-471a-a3c9-0fc0be7a4093')
        self.authorization_mgmt_client.role_assignments.create(scope=sa.id,
                                                               role_assignment_name=str(uuid.uuid4()),
                                                               parameters=role_params)

        # since the set_storage_account can only be called by a user account with access to the keys of
        # the storage account, we grant the user that created the storage account access to the vault
        # and add the storage account to the vault

        # grant the user the storage account set permission on the vault
        self.vault.properties.access_policies.append(AccessPolicyEntry(tenant_id=self.config.tenant_id,
                                                                       object_id=self._user_oid,
                                                                       permissions=Permissions(storage=[StoragePermissions.set])))
        self.keyvault_mgmt_client.vaults.create_or_update(self.config.group_name, self.vault.name, self.vault).result()


        # add the storage account to the vault using the users KeyVaultClient
        attributes = StorageAccountAttributes(enabled=True)
        keyvault_user_client.set_storage_account(vault_base_url=self.vault.properties.url,
                                                 storage_account_name=sa.name,
                                                 resource_id=sa.id,
                                                 active_key_name='key1',
                                                 auto_regenerate_key=True,
                                                 regeneration_period='P30D',
                                                 storage_account_attributes=attributes)

    @keyvaultsample
    def update_storage_account(self):
        """
        Updates a storage account in the vault.
        """
        # switch the active key for the storage account
        self.keyvault_client.update_storage_account(vault_base_url=self.vault.properties.url,
                                                    storage_account_name=self.storage_account_name,
                                                    active_key_name='key2')
        # update the key regeneration period
        self.keyvault_client.update_storage_account(vault_base_url=self.vault.properties.url,
                                                    storage_account_name=self.storage_account_name,
                                                    regenration_period='P60D')
        # stop auto rotating the storage account keys
        self.keyvault_client.update_storage_account(vault_base_url=self.vault.properties.url,
                                                    storage_account_name=self.storage_account_name,
                                                    auto_regenerate_key=False)


    @keyvaultsample
    def rotate_storage_account_keys(self):
        """
        Regenerates the primary and secondary key of a storage account managed by the vault.
        """
        # regenerate storage account keys by calling the regenerate_storage_account_key
        self.keyvault_client.regenerate_storage_account_key(vault_base_url=self.vault.properties.url,
                                                            storage_account_name=self.storage_account_name,
                                                            key_name='key1')

        self.keyvault_client.regenerate_storage_account_key(vault_base_url=self.vault.properties.url,
                                                            storage_account_name=self.storage_account_name,
                                                            key_name='key2')
    @keyvaultsample
    def get_storage_accounts(self):
        """
        Lists the storage accounts in the vault.
        """
        from azure.keyvault import StorageAccountId

        # list the storage accounts in the vault
        storage_accounts = list(self.keyvault_client.get_storage_accounts(vault_base_url=self.vault.properties.url,
                                                                          maxresults=5))
        # for each storage account parse the id and get the storage account
        for sa in storage_accounts:
            sa_id = StorageAccountId(uri=sa.id)
            storage_account = self.keyvault_client.get_storage_accounts(vault_base_url=sa_id.vault,
                                                                        storage_account_name=sa_id.name)


    @keyvaultsample
    def delete_storage_account(self):
        """
        Deletes a storage account for a vault.
        """
        self.keyvault_client.delete_storage_account(vault_base_url=self.vault.properties.url,
                                                    storage_account_name=self.storage_account_name)


    def get_user_token(self, resource):
        """
        Authenticates a user to the specified resource using device code authentication.  The user will be prompted
        to authenticate.  Once the user has authenticated they will only be prompted again if subsequent resources
        have more stringent authentication requirements.
        """
        # using the XPlat command line client id as it is available across all tenants and subscriptions
        # this would be replaced by your app id
        xplat_client_id = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
        token = None

        # if we have already authenticated the user attempt to aquire a token from the cache
        if self._user_id:
            token = self.auth_context.acquire_token(resource=resource,
                                                    user_id=self._user_id,
                                                    client_id=xplat_client_id)

        # if we were unable to aquire a token from the cache prompt to authencate the user
        if not token:
            user_code_info = self.auth_context.acquire_user_code(resource=resource,
                                                                 client_id=xplat_client_id)
            print()
            print(user_code_info['message'])
            print()
            token = self.auth_context.acquire_token_with_device_code(resource=resource,
                                                                     client_id=xplat_client_id,
                                                                     user_code_info=user_code_info)
            # store the user id of the authenticated user for subsequent authentication calls
            self._user_oid = token['objectId']
            self._user_id = token['userId']
        return token

    @keyvaultsample
    def create_account_sas_definition(self):
        """
        Creates an account sas definition, to create and manage blobs, queues, file, and tables.
        """
        from azure.storage.common import SharedAccessSignature, CloudStorageAccount
        from azure.keyvault.models import SasTokenType, SasDefinitionAttributes
        from azure.keyvault import SecretId

        # To create an account sas definition in the vault we must first create the template. The 
        # template_uri for an account sas definition is the intended account sas token signed with an arbitrary key.
        # Use the SharedAccessSignature class from azure.storage.common to create a account sas token
        sas = SharedAccessSignature(account_name=self.storage_account.name,
                                    # don't sign the template with the storage account key use key 00000000
                                    account_key='00000000')
        account_sas_template = sas.generate_account(services='bfqt',        # all services blob, file, queue and table
                                                    resource_types='sco',   # all resources service, template, object
                                                    permission='acdlpruw',  # all permissions add, create, list, process, read, update, write
                                                    expiry='2020-01-01')    # expiry will be ignored and validity period will determine token expiry

        # use the created template to create a sas definition in the vault
        attributes = SasDefinitionAttributes(enabled=True)
        sas_def = self.keyvault_client.set_sas_definition(vault_base_url=self.vault.propoerties.url,
                                                          storage_account_name=self.storage_account_name,
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
        cloud_storage_account = CloudStorageAccount(account_name=self.storage_account.name,
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
        Creates a SAS definition with access to a blob container
        """

        from azure.storage.blob import BlockBlobService, ContainerPermissions
        from azure.keyvault.models import SasTokenType, SasDefinitionAttributes
        from azure.keyvault import SecretId

        # generate the blob sas definition template
        # NOTE: that we don't use the actual storage account key to create the sas template
        #       rather the template is signed with the key 00000000

        # create a template sas token for the container
        service = BlockBlobService(account_name=self.storage_account_name,
                                   # don't sign the template with the storage account key use key 00000000
                                   account_key='00000000')
        permissions = ContainerPermissions(read=True, write=True, delete=True, list=True)
        temp_token = service.generate_container_shared_access_signature(container_name='blobcontainer',
                                                                        permission=permissions,
                                                                        expiry='2020-01-01')

        # the sas template uri for service sas definitions contains the storage entity url with the template token
        # using the BlockBlobService to construct the template uri for the container sas definition
        blob_sas_template_uri = service.make_container_url(container_name='blobcontainer',
                                                           protocol='https',
                                                           sas_token=temp_token)
        # create the sas definition in the vault
        attributes = SasDefinitionAttributes(enabled=True)
        blob_sas_def = self.keyvault_client.set_sas_definition(vault_base_url=self.vault.propoerties.url,
                                                               storage_account_name=self.storage_account_name,
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
        service = BlockBlobService(account_name=self.storage_account_name,
                                   sas_token=blob_sas_token)
        service.create_blob_from_text(container_name='blobcontainer',
                                      blob_name='blob2',
                                      text=u'test blob2 data')
        blobs = list(service.list_blobs(container_name='blobcontainer'))

        for blob in blobs:
            service.delete_blob(container_name='blobcontainer',
                                blob_name=blob.name)


if __name__ == "__main__":
    run_all_samples([StorageAccountSample()])
