targetScope = 'subscription'

@minLength(1)
@description('Primary location for all resources')
param location string

var tags = { 'azd-env-name': 'demo' }
var components = loadJsonContent('./components.json')


resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-demo'
  location: location
  tags: tags
}


// Storage account for storing deadlettered events.
module storage './components/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: 'demo-storage'
    location: location
    tags: tags
    containers: components.storageContainers
    allowBlobPublicAccess: components.storageAccount.allowBlobPublicAccess
  }
}


// Event grid domain for pub/sub of DB change events identified by audit service.
module eventGrid './components/eventgrid-domain.bicep' = {
  name: 'eventgrid'
  scope: rg
  params: {
    name: 'demo-eventgrid'
    location: location
    tags: tags
    
    deadletterDestination: {
      properties: {
        resourceId: storage.outputs.id
        blobContainerName: 'deadlettered-events'
      }
      endpointType: 'StorageBlob'
    }
    retryPolicy: {
      maxDeliveryAttempts: 10
      eventTimeToLiveInMinutes: 60
    }
    failedAuditlogsQueue: {
      properties: {
        resourceId: storage.outputs.id
        queueName: 'failed-auditlogs-queue'
        queueMessageTimeToLiveInSeconds: -1
      }
      endpointType: 'StorageQueue'
    }
  }
}


output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
