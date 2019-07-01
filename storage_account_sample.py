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
from util import KeyVaultSampleBase, get_name, keyvaultsample


class StorageAccountSample(KeyVaultSampleBase):
    """
    A collection of samples that demonstrate authenticating with the KeyVaultClient and KeyVaultManagementClient
    """

    def __init__(self, config=None):
        from azure.keyvault import KeyVaultClient, KeyVaultAuthentication, AccessToken
        from msrestazure.azure_active_directory import ServicePrincipalCredentials

        super(StorageAccountSample, self).__init__(config=config)

        self.keyvault_sp_client = KeyVaultClient(ServicePrincipalCredentials(client_id=self.config.client_id,
                                                                             secret=self.config.client_secret,
                                                                             tenant=self.config.tenant_id))

        # the key vault storage methods, storage_account_set and regenerate_storage_account_key
        # must be called by an authenticated user (not a service principal) so we create a secondary
        # client which authenticates a user using device code authentication

        # create a KeyVaultClient that authenticates as the user
        def authenticate_user(server, resource, scope, scheme):
            token = self.get_user_token(resource=resource)
            return AccessToken(scheme=token['tokenType'], token=token['accessToken'], key=None)

        self.keyvault_user_client = KeyVaultClient(
            KeyVaultAuthentication(authorization_callback=authenticate_user))

        self._user_id = None
        self._user_oid = None

    def run_all_samples(self):
        self.add_storage_account()
        self.update_storage_account()
        self.regenerate_storage_account_key()
        self.get_storage_accounts()
        self.delete_storage_account()

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
        from azure.mgmt.authorization import AuthorizationManagementClient

        self.config.storage_account_name = get_name('sa', '')

        # only user accounts with access to the storage account keys can add a storage account to
        # a vault.  For this reason this sample creates the storage account with a user account
        # authenticated through device login rather than the service principal credentials used
        # in other samples.
        # create the StorageManagementClient with user token credentials
        user_token_creds = AADTokenCredentials(
            self.get_user_token('https://management.core.windows.net/'))

        print('creating storage account %s' % self.config.storage_account_name)
        storage_mgmt_client = StorageManagementClient(
            user_token_creds, self.config.subscription_id)

        # create the storage account
        sa_params = StorageAccountCreateParameters(sku=Sku(SkuName.standard_ragrs),
                                                   kind=Kind.storage,
                                                   location=self.config.location)
        sa = storage_mgmt_client.storage_accounts.create(resource_group_name=self.config.group_name,
                                                         account_name=self.config.storage_account_name,
                                                         parameters=sa_params).result()

        # the KeyVault service must be given the "Storage Account Key Operator Service Role" on the
        # storage account before the storage account can be added to the vault

        print('granting Azure Key Vault the "Storage Account Key Operator Service Role" on the storage account')
        # find the role definition for "Storage Account Key Operator Service Role"
        filter_str = 'roleName eq \'Storage Account Key Operator Service Role\''
        authorization_mgmt_client = AuthorizationManagementClient(
            user_token_creds, self.config.subscription_id)
        role_id = list(authorization_mgmt_client.role_definitions.list(
            scope='/', filter=filter_str))[0].id

        # create a role assignment granting the key vault service principal this role
        role_params = RoleAssignmentCreateParameters(role_definition_id=role_id,
                                                     # the Azure Key Vault service id
                                                     principal_id='93c27d83-f79b-4cb2-8dd4-4aa716542e74')
        authorization_mgmt_client.role_assignments.create(scope=sa.id,
                                                          role_assignment_name=str(
                                                              uuid.uuid4()),
                                                          parameters=role_params)

        # since the set_storage_account can only be called by a user account with access to the keys of
        # the storage account, we grant the user that created the storage account access to the vault
        # and add the storage account to the vault
        vault = self.get_sample_vault()

        # grant the user access the vault
        self.grant_access_to_sample_vault(vault, self._user_oid)

        # add the storage account to the vault using the users KeyVaultClient
        print('adding storage acount %s to vault %s' %
              (self.config.storage_account_name, vault.name))
        attributes = StorageAccountAttributes(enabled=True)
        self.keyvault_user_client.set_storage_account(vault_base_url=self.sample_vault_url,
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
        print('updating storage account active key')
        self.keyvault_sp_client.update_storage_account(vault_base_url=self.sample_vault_url,
                                                       storage_account_name=self.config.storage_account_name,
                                                       active_key_name='key2')

        # update the key regeneration period
        print('updating storage account regeneration period')
        # self.keyvault_sp_client.update_storage_account(vault_base_url=self.sample_vault_url,
        #                                                storage_account_name=self.config.storage_account_name,
        #                                                regenration_period='P60D')

        print('disabling automatic key regeneration')
        # stop auto rotating the storage account keys
        self.keyvault_sp_client.update_storage_account(vault_base_url=self.sample_vault_url,
                                                       storage_account_name=self.config.storage_account_name,
                                                       auto_regenerate_key=False)

    @keyvaultsample
    def regenerate_storage_account_key(self):
        """
        Regenerates a key of a storage account managed by the vault.
        """
        # regenerate storage account keys by calling the regenerate_storage_account_key
        # Note that the regenerate_storage_account_key method can only be called by a user account
        # not a service principal so we use teh keyvault_user_client created in __init__()
        print('regenerating storage account key1')
        self.keyvault_user_client.regenerate_storage_account_key(vault_base_url=self.sample_vault_url,
                                                                 storage_account_name=self.config.storage_account_name,
                                                                 key_name='key1')

    @keyvaultsample
    def get_storage_accounts(self):
        """
        Lists the storage accounts in the vault, and gets each.
        """
        from azure.keyvault import StorageAccountId

        # list the storage accounts in the vault
        print('list and get storage accounts managed by the vault')
        storage_accounts = list(self.keyvault_sp_client.get_storage_accounts(vault_base_url=self.sample_vault_url,
                                                                             maxresults=5))
        # for each storage account parse the id and get the storage account
        for sa in storage_accounts:
            sa_id = StorageAccountId(uri=sa.id)
            storage_account = self.keyvault_sp_client.get_storage_account(vault_base_url=sa_id.vault,
                                                                          storage_account_name=sa_id.name)
            print(sa_id.name, storage_account.resource_id)

    @keyvaultsample
    def delete_storage_account(self):
        """
        Deletes a storage account from a vault.
        """
        print('deleting storage account %s from the vault' %
              self.config.storage_account_name)
        self.keyvault_sp_client.delete_storage_account(vault_base_url=self.sample_vault_url,
                                                       storage_account_name=self.config.storage_account_name)

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
            token = self.config.auth_context.acquire_token(resource=resource,
                                                           user_id=self._user_id,
                                                           client_id=xplat_client_id)

        # if we were unable to aquire a token from the cache prompt to authencate the user
        if not token:
            user_code_info = self.config.auth_context.acquire_user_code(resource=resource,
                                                                        client_id=xplat_client_id)
            print()
            print(user_code_info['message'])
            print()
            token = self.config.auth_context.acquire_token_with_device_code(resource=resource,
                                                                            client_id=xplat_client_id,
                                                                            user_code_info=user_code_info)

            # store the user id of the authenticated user for subsequent authentication calls
            self._user_oid = token['oid']
            self._user_id = token['userId']
        return token


if __name__ == "__main__":
    StorageAccountSample().run_all_samples()
