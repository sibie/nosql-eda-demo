param name string
param location string = resourceGroup().location
param tags object = {}
param sku object = { name: 'Standard_LRS' }
param kind string = 'StorageV2'
param minimumTlsVersion string = 'TLS1_2'
param allowBlobPublicAccess bool
param containers array = []


// Storage account setup in Azure.
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: sku
  kind: kind
  properties: {
    minimumTlsVersion: minimumTlsVersion
    allowBlobPublicAccess: allowBlobPublicAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }

  resource blobServices 'blobServices' = if (!empty(containers)) {
    name: 'default'
    resource container 'containers' = [for container in containers: {
      name: container.name
      properties: {
        publicAccess: container.?publicAccess ?? 'None'
      }
    }]
  }
}

resource storageQueues 'Microsoft.Storage/storageAccounts/queueServices@2023-01-01' = {
  name: 'default'
  parent: storage
}

// Queue for storing failed audit service payloads for inspection.
resource failedAuditlogsQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01' = {
  name: 'failed-auditlogs-queue'
  parent: storageQueues
}

output name string = storage.name
output id string = storage.id
output primaryEndpoints object = storage.properties.primaryEndpoints
