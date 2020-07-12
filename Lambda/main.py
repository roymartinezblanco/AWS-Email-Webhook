# -*- coding: utf-8 -*-

from datetime import datetime
from botocore.vendored import requests
from email.parser import Parser
import json, boto3, os, email,urllib.parse



s3_client = boto3.resource('s3')



class activation:
  def __init__(self, propertyname = None, propertyver = None,accountname = None,submittedby = None,network = None,endpoint = None, headers = None):
    self.propertyname = propertyname
    self.propertyver = propertyver
    self.accountname = accountname
    self.propertyver = propertyver
    self.network = network
    self.submittedby = submittedby
    self.endpoint = endpoint
    self.headers = headers



def print_with_timestamp(*args):
    print(datetime.utcnow().isoformat(), *args)

def get_config(network):
    file_content = s3_client.Object('ak-activation-email', ('configurations/'+network.lower()+'-webhooks.json')).get()['Body'].read().decode('utf-8')
    return json.loads(file_content)


def spam(receipt):
    if (receipt['spfVerdict']['status'] == 'FAIL' or
            receipt['dkimVerdict']['status'] == 'FAIL' or
            receipt['spamVerdict']['status'] == 'FAIL' or
            receipt['virusVerdict']['status'] == 'FAIL'):
        
        return True
    else:
        return False

def findConfiguration(akamaiActivation,configFile):

    for el in configFile['accounts']:
        if akamaiActivation.endpoint is None:
            if el['name'] == akamaiActivation.accountname:
                print_with_timestamp("Found Account: ",akamaiActivation.accountname)
                if el['properties']:
                    for hook in el['properties']:
                        
                        if hook['name'] == akamaiActivation.propertyname:
                            print_with_timestamp("Found Webhook for: ",akamaiActivation.propertyname)
                            akamaiActivation.endpoint = hook['endpoint']
                            akamaiActivation.headers = hook['headers']
                            break
        else:
            break
    return

def identifyActivation(akamaiActivation,msg):
    
    print_with_timestamp("Reading Activation Email")
    for line in str(msg).splitlines():
        if akamaiActivation.propertyname is None or akamaiActivation.accountname is None or akamaiActivation.propertyver is None or akamaiActivation.network is None or akamaiActivation.submittedby is None: 
            if akamaiActivation.propertyname is None: 
                if(line.find("Property Name:") == 0):
                    akamaiActivation.propertyname = line.split(":")[1].strip()
                    print_with_timestamp("Property Name: ", akamaiActivation.propertyname)
            if akamaiActivation.propertyver is None: 
                if(line.find("Property Version:") == 0):
                    akamaiActivation.propertyver =  line.split(":")[1].strip()
                    print_with_timestamp("Property Version: ", akamaiActivation.propertyver)
            if akamaiActivation.accountname is None: 
                if(line.find("Account Name:") == 0):
                    akamaiActivation.accountname = line.split(":")[1].strip()
                    print_with_timestamp("Account Name: ", akamaiActivation.accountname)
            if akamaiActivation.network is None: 
                if(line.find("successfully activated on") > -1):
                    akamaiActivation.network = line.split("successfully activated on")[1].strip().replace("!", "")
                    print_with_timestamp("Network: ", akamaiActivation.network)
            if akamaiActivation.submittedby is None: 
                if(line.find("Submitted By:") == 0):
                    akamaiActivation.submittedby = line.split(":")[1].strip()
                    if akamaiActivation.submittedby == "NA NA":
                        akamaiActivation.submittedby = "Automated"
                    print_with_timestamp("Submitted By: ", akamaiActivation.submittedby)
                    
        else:
            break
    return akamaiActivation
    
def notify(akamaiActivation):
    if akamaiActivation.endpoint is not None:
        akamaiActivation.endpoint = urllib.parse.unquote(akamaiActivation.endpoint)
        print_with_timestamp('Starting Webhook:', akamaiActivation.endpoint)
        try:
            http = requests.Session()
            if(akamaiActivation.endpoint):
                if (akamaiActivation.headers):
                    result = http.get(akamaiActivation.endpoint, headers=akamaiActivation.headers)
                    print_with_timestamp('Webhook Response: '+str(result.status_code))
                else:
                    result = http.get(akamaiActivation.endpoint, headers=None)
                    print_with_timestamp('Webhook Response: '+str(result.status_code))
            return True
        except Exception as e2: 
            print_with_timestamp(e2)
            raise e2

    else:
        print_with_timestamp("Webhook: Endpoint not found")
     

                   

def run(event=None, context=None):
    
    
    akamaiActivation = activation()

    print_with_timestamp('Starting - spam-filter')

    ses_notification = event['Records'][0]['ses']
    message_id = ses_notification['mail']['messageId']
    receipt = ses_notification['receipt']
    sender = ses_notification['mail']['commonHeaders']['returnPath']
    
    print_with_timestamp('Received message from:', sender)

    print_with_timestamp('Processing message:', message_id)

    # Check if any spam check failed
    if spam(receipt):
        print_with_timestamp('Rejected message:', message_id)
    else:   
        print_with_timestamp('Accepting message:', message_id)
        try:
            
            # Testing with saved s3 Files
            if sender == 'human@example.com':
                # Human Activation
                message_id = 'examples/human'
            if sender == 'automated@example.com':
                # Automated Activation
                message_id = 'examples/automated'
         
            mail_obj = s3_client.Object('ak-activation-email', message_id)
            msg = email.message_from_bytes(mail_obj.get()['Body'].read())

            
            print_with_timestamp("Fetching Email Body from s3: ",message_id)
            akamaiActivation = identifyActivation(akamaiActivation,msg)  
            
            if akamaiActivation.submittedby != "Automated":
                print_with_timestamp("None Pipeline Activation, Triggering Webhook event")
                print_with_timestamp("Fetching '"+akamaiActivation.network+"' Configuration")
                findConfiguration(akamaiActivation,get_config(akamaiActivation.network))
                notify(akamaiActivation)
                if sender == 'noreply@akamai.com':
                    response = mail_obj.delete_object('ak-activation-email', message_id)
                    print_with_timestamp("Object '"+message_id+"' Removed from s3:",response.status_code)
           
                    return True
            else:
                print_with_timestamp("Pipeline Activation, No Webhook event Triggered")
                return False
    
            
        except Exception as e2:
            print_with_timestamp(e2)
            print_with_timestamp('An error occurred: ', message_id)
            raise e2

        return None
