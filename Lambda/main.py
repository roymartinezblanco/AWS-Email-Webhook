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


def webhook(u,h):
    u = urllib.parse.unquote(u)
    print_with_timestamp('Starting Webhook:', u)
    try:
        http = requests.Session()
        if(u):
            if (h):
                result = http.get(u, headers=h)
                print_with_timestamp('Webhook Response: '+str(result.status_code))
            else:
                result = http.get(u, headers=None)
                print_with_timestamp('Webhook Response: '+str(result.status_code))
        return True
    except Exception as e2: 
        print_with_timestamp(e2)
        raise e2
def get_config(network):
    file_content = s3_client.Object('ak-activation-email', (network.lower()+'-webhooks.json')).get()['Body'].read().decode('utf-8')
    return json.loads(file_content)


def spam(receipt):
    if (receipt['spfVerdict']['status'] == 'FAIL' or
            receipt['dkimVerdict']['status'] == 'FAIL' or
            receipt['spamVerdict']['status'] == 'FAIL' or
            receipt['virusVerdict']['status'] == 'FAIL'):
        
        return True
    else:
        return False
def findConfiguration(akEvent,configFile):

    for el in configFile['accounts']:
        if akEvent.endpoint is None:
            if el['name'] == akEvent.accountname:
                print_with_timestamp("Found Account: ",akEvent.accountname)
                if el['webhooks']:
                    for hook in el['webhooks']:
                        
                        if hook['name'] == akEvent.propertyname:
                            print_with_timestamp("Found Webhook for: ",akEvent.propertyname)
                            akEvent.endpoint = hook['endpoint']
                            akEvent.headers = hook['headers']
                            break
        else:
            break
    return

def identifyActivation(msg):
    akEvent = activation()
    print_with_timestamp("Reading Activation Email")
    for line in str(msg).splitlines():
        if akEvent.propertyname is None or akEvent.accountname is None or akEvent.propertyver is None or akEvent.network is None or akEvent.submittedby is None: 
            if akEvent.propertyname is None: 
                if(line.find("Property Name:") == 0):
                    akEvent.propertyname = line.split(":")[1].strip()
                    print_with_timestamp("Property Name: ", akEvent.propertyname)
            if akEvent.propertyver is None: 
                if(line.find("Property Version:") == 0):
                    akEvent.propertyver =  line.split(":")[1].strip()
                    print_with_timestamp("Property Version: ", akEvent.propertyver)
            if akEvent.accountname is None: 
                if(line.find("Account Name:") == 0):
                    akEvent.accountname = line.split(":")[1].strip()
                    print_with_timestamp("Account Name: ", akEvent.accountname)
            if akEvent.network is None: 
                if(line.find("successfully activated on") > -1):
                    akEvent.network = line.split("successfully activated on")[1].strip().replace("!", "")
                    print_with_timestamp("Network: ", akEvent.network)
            if akEvent.submittedby is None: 
                if(line.find("Submitted By:") == 0):
                    akEvent.submittedby = line.split(":")[1].strip()
                    if akEvent.submittedby == "NA NA":
                        akEvent.submittedby = "Automated"
                    print_with_timestamp("Submitted By: ", akEvent.submittedby)
                    
        else:
            break
    return akEvent
    
def notify(akEvent,filename):
    if akEvent.endpoint is not None:
        #print_with_timestamp("Webhook Sent: "+str(webhook(akEvent.endpoint,akEvent.headers)))
        akEvent.endpoint = urllib.parse.unquote(akEvent.endpoint)
        print_with_timestamp('Starting Webhook:', akEvent.endpoint)
        try:
            http = requests.Session()
            if(akEvent.endpoint):
                if (akEvent.headers):
                    result = http.get(akEvent.endpoint, headers=akEvent.headers)
                    print_with_timestamp('Webhook Response: '+str(result.status_code))
                else:
                    result = http.get(akEvent.endpoint, headers=None)
                    print_with_timestamp('Webhook Response: '+str(result.status_code))
            return True
        except Exception as e2: 
            print_with_timestamp(e2)
            raise e2

    else:
        print_with_timestamp("Webhook: Endpoint not found")
     

                   

def run(event=None, context=None):
    
    
    endpoint = None
    headers = None
    jsonObject = None
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
            filename = message_id
            if sender == 'human@example.com':
                # Human Activation
                filename = '6srfqio8l51slu6dn9u2otkdkd10oms4i7vmqko1'
            if sender == 'automated@example.com':
                # Automated Activation
                filename = 'ds1u48ce7n8aapfkkii891hob2svcu1atv940vg1'
         
            mail_obj = s3_client.Object('ak-activation-email', filename)
            msg = email.message_from_bytes(mail_obj.get()['Body'].read())

            
            print_with_timestamp("Fetching Email Body from s3: ",filename)
            akEvent = identifyActivation(msg)  
            
            if akEvent.submittedby != "Automated":
                print_with_timestamp("None Pipeline Activation, Triggering Webhook event")
                print_with_timestamp("Fetching '"+akEvent.network+"' Configuration")
                configFile = get_config(akEvent.network)
                findConfiguration(akEvent,configFile)
                notify(akEvent,filename)
                if sender == 'noreply@akamai.com':
                    response = mail_obj.delete_object('ak-activation-email', filename)
                    print_with_timestamp("Object '"+filename+"' Removed from s3:",response.status_code)
           
                    return True
            else:
                print_with_timestamp("Pipeline Activation, No Webhook event Triggered")
                return False
        
           
            
        except Exception as e2:
            print_with_timestamp(e2)
            print_with_timestamp('An error occurred: ', message_id)
            raise e2

        return None