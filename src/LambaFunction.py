# -*- coding: utf-8 -*-

from datetime import datetime
from botocore.vendored import requests
from email.parser import Parser
import json, boto3, os, email,urllib.parse



s3_client = boto3.resource('s3')

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
        return False
def get_config(network):
    file_content = s3_client.Object('ak-activation-email', (network.lower()+'-webhooks.json')).get()['Body'].read().decode('utf-8')
    return json.loads(file_content)
    
def run(event=None, context=None):
    print_with_timestamp('Starting - spam-filter')

    ses_notification = event['Records'][0]['ses']
    message_id = ses_notification['mail']['messageId']
    receipt = ses_notification['receipt']

    
    
    print_with_timestamp('Processing message:', message_id)

    # Check if any spam check failed
    if (receipt['spfVerdict']['status'] == 'FAIL' or
            receipt['dkimVerdict']['status'] == 'FAIL' or
            receipt['spamVerdict']['status'] == 'FAIL' or
            receipt['virusVerdict']['status'] == 'FAIL'):
        print_with_timestamp('Rejected message:', message_id)
    
    else:
        print_with_timestamp('Accepting message:', message_id)
      
        try:
            filename = message_id
            #filename = '6srfqio8l51slu6dn9u2otkdkd10oms4i7vmqko1'
            mail_obj = s3_client.Object('ak-activation-email', filename)
            msg = email.message_from_bytes(mail_obj.get()['Body'].read())
        

            print_with_timestamp("Email Fetched")
            propertyname = None
            propertyver = None
            accountname = None
            network = None
            
            for line in str(msg).splitlines():

                if propertyname is None or accountname is None or propertyver is None or network is None:
                    if propertyname is None: 
                        if(line.find("Property Name:") == 0):
                            propertyname = line.split(":")[1].strip()
                            print_with_timestamp("Property Name: ", propertyname)
                    if propertyver is None: 
                        if(line.find("Property Version:") == 0):
                            propertyver = line.split(":")[1].strip()
                            print_with_timestamp("Property Version: ", propertyver)
                    if accountname is None: 
                        if(line.find("Account Name:") == 0):
                            accountname = line.split(":")[1].strip()
                            print_with_timestamp("Account Name: ", accountname)
                    if network is None: 
                        if(line.find("successfully activated on") > -1):
                            network = line.split("successfully activated on")[1].strip().replace("!", "")
                            print_with_timestamp("Network: ", network)
                else:
                    break
                
            print_with_timestamp("Fetching Config")
            
            jsonObject = get_config(network)
  
            endpoint = None
            headers = None
       
            for el in jsonObject['accounts']:
                if endpoint is None:
                    if el['name'] == accountname:
                        print_with_timestamp("Found Account: ",accountname)
                        if el['webhooks']:
                            for hook in el['webhooks']:
                                
                                if hook['name'] == propertyname:
                                    print_with_timestamp("Found Webhook for: ",propertyname)
                                    endpoint = hook['endpoint']
                                    headers = hook['headers']
                                    break
                else:
                    break
            if endpoint is not None:
                print_with_timestamp("Webhook Sent: "+str(webhook(endpoint,headers)))
                try:
                    if filename != '6srfqio8l51slu6dn9u2otkdkd10oms4i7vmqko1':
                        response = s3_client.delete_object('ak-activation-email', filename)
                        print_with_timestamp("Object '"+filename+"' Removed from s3")
                except Exception as e:
                    print_with_timestamp(e)
                    print_with_timestamp('An error occurred: ', message_id)

            else:
                print_with_timestamp("Webhook Sent: False, endpoint not found")
                
        except Exception as e2:
            print_with_timestamp(e2)
            print_with_timestamp('An error occurred: ', message_id)
            raise e2

        return None
        
