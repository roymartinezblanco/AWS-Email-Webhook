# AWS-Email-Webhook

TLDR; This project is meant to provide a reference architecture to implement an email-based webhook that would trigger Jobs/Builds on a system like `Jenkins`.

---

A challenge we face in DevOps is when we can't notify/trigger a pipeline about a change in a system/service (outside of our normal email activation notifications). Not having this capability is a challenge especially when Akamai Personal makes changes to a configuration making it `out of sync`. 

This solution will fill that void need by providing the `how-to` and if there is interest we can also provide this as a service(POC). In this example, we will be receiving an Akamai Activation Notification, `process` it, and trigger a webhook. 

### What it does:
* Receive and Extract details from email
* Identify Automated Activations
* Send Webhook
* Configure per Property Webhooks

### How it works:
![Documentation/flow.png](Documentation/flow.png)

This solution is made using AWS Services to quickly build the functionality needed:

* SES
* s3
* Lambda

AWS SES allows us to accept emails and to send them for processing. Lambda is then used to parse the email body (saved in AWS s3).

>Note: This example does not encrypt saved emails but you can do so within `SES`.

This function rejects spam, parses the email looking for details like Account Name, property name, network, who activated (Human or API), etc. Once we know for what account/config the notification is for we will look for any configured Webhook from a file also in s3.

Configured Webhook? For this POC that I've created is a `JSON` file that will live in s3, this file will have any configured webhook for a give account/Property. The function once it has made sure it's not spam and it has the details of the activation, using the same details it will look for any webhook under the same accountname and propetyname. Once it finds a webhook for the current activation it will make a network request `GET` to the URL and with the `HTTP` headers configured.

## Configuration Example

As you can see you can add custom headers to the `headers` field if needed.

```json
{
  "accounts": [
    {
      "name": "Global Consulting Services",
      "proerties": [
        {
          "name": "roymartinez.dev",
          "endpoint": "http%3A%2F%2Fexample.com%2Fgeneric-webhook-trigger%2Finvoke%3Ftoken%3D<some-token>",
          "headers": { "Content-Type": "application/json" ,"User-Agent":"Webhook"}
        }
      ]
    }
  ]
}
```

## Usage

Once we have configured s3, SES, Lamda, and IAM all we need to do is add the configured email to the notification list `webhook@example.com`.
![Activation](Documentation/Notification.jpg)

---

# AWS Setup


![](Documentation/s3.png) **S3** 

We need a bucket to store our messages, no special requirements for it except the policy to be used below.

Please use this guide if needed: [How to create a bucket](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-bucket.html)

Upload both configuration example files found [here](Configuration) and if you want you can also upload the sample email for testing.


![](Documentation/lambda.png) **Lambda**

This is where most of the work goes, but for now, just create a function ([update IAM policy](Policies/s3.policy.json)), and below we have a section on the script itself.

Apart from that access needed there aren't many changes around the function (excluding the code). The only thing that was added was 2 test cases that are based on the `SES` Example:
* [Human](Examples/Human.Testemail.json) 
* [Automated](Examples/Human.Testemail.json)

If you compare them to the "Official" `SES` example the only change the have is the return paths that are used later in the code.

```"returnPath": "automated@example.com"```

```"returnPath": "human@example.com"```

[How to create a function](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html)


![](Documentation/ses.png) **SES**

Once you have created/configured `s3` and `Lambda` we can now set up `SES`.

Steps:
1. [Validate your domain](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-domains.html). ![](Documentation/validatedomain.ses.jpg)
2. [Configure IAM Policy](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/sending-authorization-policy-examples.html#sending-authorization-policy-example-from)
3. [Create a Rule set](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-receipt-rule-set.htm) ![](Documentation/SES.rules.jpg)
 in this rule set we will need 2 actions:
   * Store Message in `S3`
   * Trigger `Lambda`


## IAM Policies

![](Documentation/ses.png) **SES**

For SES I created a policy to limit who can send emails to this setup. In summary, we need to add a condition for the sender and in our example its the noreply@akamai.com.
[Full SES IAM Policy Example](Policies/ses.policy.json)

```json
{
  "Condition": {
    "StringEquals": {
      "ses:FromAddress": "noreply@akamai.com"
    }
  }
}
```

![](Documentation/s3.png) **S3**

SES will be storing the messages we need to permit it to do so. [Full s3 IAM Policy Example](Policies/s3.policy.json) 

```json
{
  "Principal": {
    "Service": "ses.amazonaws.com"
  },
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<changeme>/*"
}
```

![](Documentation/lambda.png) **Lambda**

Lastly, Lamdba needs to be invoked by `SES`. [Full Lambda IAM Policy Example](Policies/lambda.policy.json)

```json
{
  "Principal": {
    "Service": "ses.amazonaws.com"
  },
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:<changeme>"
}
```

---
# Lambda Function

> Any recommendations are welcomed that might improve this.

`SES` will trigger our function and provide details in the incoming message.

Functionality:
* Filter out Spam
* Read the message from s3
* Read Configuration from s3
* Find and Extract data
* Send Webhook
* Delete message from s3

Using the `SES` event, we can exact information like the `messageId` (important since this is the name of the file in `S3`) and `from email`. Because we are filtering with `IAM` the emails we accept messages from we don't need additional functionality but we do use spam validation to drop any unwanted (just in case) emails.

The function once it extracts the values from the email ([see example email](Examples/Email.txt)), it reads the [Webhook Config file](Configuration/production-webhooks.json) in s3. This "service" is meant to be a multi-tenant solution and because of it the config is structured in the following way:

> Accountname ==> Properties (Akamai Config) ==> Webhook

We should only have one Hook per property but many properties per account (all this comes from the email). Because Akamai has two networks `['staging','production']` a second configuration file can also be used (in the future we can also merge both).

Once all of the above is ready you can test the function by using the configured tests mentioned above and the reason for this is that Akamai Activations are `Automated` ([Terraform](https://www.terraform.io/docs/providers/akamai/index.html), etc) have a null value in the `submitted by` field. Knowing this I used a hardcoded email from the test `['human@example.com','automated@example.com']` to simulate what would happen, since I want to trigger a webhook only if a human-made a change manually that would make Terraform or our VS to be out of sync, thus, trigger a merge of what is now active vs what is store in my git.

![](Documentation/lamdbalog.jpg)

## Have fun!...

---    

## Contribute

Want to contribute? Sure why not! just let me know!

## Author

I’m a photography enthusiast but in business hours I am a Computer Science analyst. More about me here: [](https://roymartinez.dev)

## Licensing

I am providing code and resources in this repository to you under an open-source license. Because this is my repository, the license you receive to my code and resources is from me and not my employer (Akamai).

```
Copyright 2019 Roy Martinez

Creative Commons Attribution 4.0 International License (CC BY 4.0)

http://creativecommons.org/licenses/by/4.0/
```