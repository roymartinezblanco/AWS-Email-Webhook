# AWS-Email-Webhook

## Description

This project is meant to provide a reference Architecture to implement a email based webhook that would trigger Jobs/Builds on a system like `Jenkins`.


![Configuration/Arch.png](Documentation/Arch.png)

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