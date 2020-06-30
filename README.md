# AWS-Email-Webhook

This project is meant to provide a reference Architecture to implement a email based webhook that would trigger Jobs/Builds on a system like `Jenkins`.

What can it do: s
* Receive and Extract details from email
* Identify Automated Activations
* Send Webhook
* Configure per Property Webhooks


### Why?
The problem we face is that we can't notify customers pipeline about a change on our configurations ourside of our normal email activation notifications. The idea with this project is to provide the `how to` and if there is interest we can also provide this as a POC.

Not having this capability is a challenge specially when Akamai Personal makes changes to a configuration making it `out of sync`. 

With this solution will receive Akamai Activation Notification `process` them and trigger a webhook. This webhook and then be used to trigger something like a `Jenkins` Job.



How

## Architecture


This solution is made using AWS Services to quickly build the functionality needed.

Example usecase: Email based notifications, like Akamai Delivery Configuration Activation Email.


## Configuration 

```json
{
  "accounts": [
    {
      "name": "Global Consulting Services",
      "webhooks": [
        {
          "name": "roymartinez.dev",
          "endpoint": "http%3A%2F%2Fexample.com%2Fgeneric-webhook-trigger%2Finvoke%3Ftoken%3D7bf349ff546c43b9b62fb2b6e72f0a58",
          "headers": { "Content-Type": "application/json" ,"User-Agent":"Webhook"}
        }
      ]
    }
  ]
}
```
## Usage

webhook@roymartinez.dev