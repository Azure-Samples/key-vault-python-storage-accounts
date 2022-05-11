---
services: key-vault
platforms: python
author: schaabs
---

***DISCLAIMER: The data plane samples in this repo are for `azure-keyvault`. In the interest of simplifying APIs, `azure-keyvault` and `KeyVaultClient` have been split into separate packages and clients. For samples using these latest packages, please visit:***

- [`azure-keyvault-certificates` samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/keyvault/azure-keyvault-certificates/samples)
- [`azure-keyvault-keys` samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/keyvault/azure-keyvault-keys/samples)
- [`azure-keyvault-secrets` samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/keyvault/azure-keyvault-secrets/samples)

***This repo is archived since `azure-keyvault-x` packages have become stable. For the latest management plane package, please visit [`azure-mgmt-keyvault`](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/keyvault/azure-mgmt-keyvault).***

***DISCLAIMER: If you are looking to migrate from `azure-keyvault` to `azure-keyvault-x`, we suggest getting started with the following migration guides:***

- [`azure-keyvault-certificates` migration guide](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/keyvault/azure-keyvault-certificates/migration_guide.md)
- [`azure-keyvault-keys` migration guide](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/keyvault/azure-keyvault-keys/migration_guide.md)
- [`azure-keyvault-secrets` migration guide](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/keyvault/azure-keyvault-secrets/migration_guide.md)

# Managing storage account keys in Azure Key Vault using the Azure Python SDK

This Sample repo includes sample code demonstrating common mechanism for managing storage account keys using Key Vault.

## Samples in this repo
* storage_account_sample.py
  * add_storage_account -- Creates a storage account then adds the storage account to the vault to manage its keys.
  * update_storage_account -- Updates a storage account in the vault.
  * regenerate_storage_account_key -- Regenerates a key of a storage account managed by the vault.
  * get_storage_accounts -- Lists the storage accounts in the vault, and gets each.
  * delete_storage_account -- Deletes a storage account from a vault.
* sas_definition_sample.py
  * create_account_sas_definition -- Creates an account sas definition, to manage storage account and its entities.
  * create_blob_sas_defintion -- Creates a service SAS definition with access to a blob container.
  * get_sas_definitions -- List the sas definitions for the storage account, and get each.

## Running The samples
1. If you don't already have it, [install Python](https://www.python.org/downloads/).

2. We recommend using a [virtual environment](https://docs.python.org/3/tutorial/venv.html) to run this example, but it's not mandatory. You can initialize a virtual environment this way:

    ```
    pip install virtualenv
    virtualenv mytestenv
    cd mytestenv
    source bin/activate
    ```

3. Clone the repository.

    ```
    git clone https://github.com/Azure-Samples/key-vault-python-authentication.git
    ```

4. Install the dependencies using pip.

    ```
    cd key-vault-python-storage-accounts
    pip install -r requirements.txt
    ```

5. Create an Azure service principal, using 
[Azure CLI](http://azure.microsoft.com/documentation/articles/resource-group-authenticate-service-principal-cli/),
[PowerShell](http://azure.microsoft.com/documentation/articles/resource-group-authenticate-service-principal/)
or [Azure Portal](http://azure.microsoft.com/documentation/articles/resource-group-create-service-principal-portal/).

6. Export these environment variables into your current shell. 

    ```
    export AZURE_TENANT_ID={your tenant id}
    export AZURE_SUBSCRIPTION_ID={your subscription id}
    export AZURE_CLIENT_ID={your service principal AppID}
    export AZURE_CLIENT_OID={your service principal OID}
    export AZURE_CLIENT_SECRET={your service principal secret}
    ```

7. Run the samples, optionally specifying a space delimited list of specific samples to run.

    ```
    python run_sample.py
    ```

##Note## Certain portions of this sample require authenticated user to execute.  For this reason the sample will prompt
the user to authenticate with a device code.  For more details see in-line comments in storage_acount_sample.py

## Minimum Requirements
Python 2.7, 3.3, or 3.4.
To install Python, please go to https://www.python.org/downloads/

## More information

* What is Key Vault? - https://docs.microsoft.com/en-us/azure/key-vault/key-vault-whatis
* Get started with Azure Key Vault - https://docs.microsoft.com/en-us/azure/key-vault/key-vault-get-started
* Azure Key Vault General Documentation - https://docs.microsoft.com/en-us/azure/key-vault/
* Azure Key Vault REST API Reference - https://docs.microsoft.com/en-us/rest/api/keyvault/
* Azure SDK for Python Documentation - http://azure-sdk-for-python.readthedocs.io/en/latest/
* Azure Active Directory Documenation - https://docs.microsoft.com/en-us/azure/active-directory/
  
# Contributing

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information 
see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) 
with any additional questions or comments.
