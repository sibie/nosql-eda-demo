param name string
param location string = resourceGroup().location
param tags object = {}

param subscriberAppDomain string = '<APP_BASE_URL>'
param deadletterDestination object
param retryPolicy object
param failedAuditlogsQueue object


resource demoEventGridDomain 'Microsoft.EventGrid/domains@2023-12-15-preview' = {
  name: name
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    inputSchema: 'CloudEventSchemaV1_0'
    publicNetworkAccess: 'Enabled'
  }
}


// Lets assume that we only have two collections in our API DB - 'blog_posts' and 'comments'.
// Generally we want to have a separate topic for each collection change event type. 

resource blogPostsEvents 'Microsoft.EventGrid/domains/topics@2023-12-15-preview' = {
  parent: demoEventGridDomain
  name: 'db-blog-posts-events'
}

resource commentsEvents 'Microsoft.EventGrid/domains/topics@2023-12-15-preview' = {
  parent: demoEventGridDomain
  name: 'db-comments-events'
}

// This topic transmits failed audit request payloads to a storage queue for inspection.
resource failedAuditlogsEvents 'Microsoft.EventGrid/domains/topics@2023-12-15-preview' = {
  parent: demoEventGridDomain
  name: 'failed-auditlogs-events'
}

// For each topic, we can create any number of subscriptions to clients that need to consume events of that type as part of its task.
// For this demo, we'll just have one per topic mapped to a dummy service to showcase how it all ties together.

resource blogPostEventsDemoSubscription 'Microsoft.EventGrid/domains/topics/eventSubscriptions@2023-12-15-preview' = {
  parent: blogPostsEvents
  name: 'blog-posts-subscription'
  properties: {
    destination: {
      properties: {
        maxEventsPerBatch: 1
        preferredBatchSizeInKilobytes: 64
        endpointUrl: '${subscriberAppDomain}/webhooks/blog_posts'
      }
      endpointType: 'WebHook'
    }
    eventDeliverySchema: 'CloudEventSchemaV1_0'
    deadLetterDestination: deadletterDestination
    retryPolicy: retryPolicy
  }
}

resource commentsEventsDemoSubscription 'Microsoft.EventGrid/domains/topics/eventSubscriptions@2023-12-15-preview' = {
  parent: commentsEvents
  name: 'comments-subscription'
  properties: {
    destination: {
      properties: {
        maxEventsPerBatch: 1
        preferredBatchSizeInKilobytes: 64
        endpointUrl: '${subscriberAppDomain}/webhooks/comments'
      }
      endpointType: 'WebHook'
    }
    eventDeliverySchema: 'CloudEventSchemaV1_0'
    deadLetterDestination: deadletterDestination
    retryPolicy: retryPolicy
  }
}

// This subscription wires failed audit payloads from the topic we set for this use case -> queue in storage-account.bicep
resource failedAuditlogsEventsDeadletterAuditlogs 'Microsoft.EventGrid/domains/topics/eventSubscriptions@2023-12-15-preview' = {
  parent: failedAuditlogsEvents
  name: 'failed-auditlogs'
  properties: {
    destination: failedAuditlogsQueue
    eventDeliverySchema: 'CloudEventSchemaV1_0'
    retryPolicy: retryPolicy
  }
}

output EG_SERVICE_PRINCIPAL_ID string = demoEventGridDomain.identity.principalId
