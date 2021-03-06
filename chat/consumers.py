import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from .models import Message
from django.contrib.auth import get_user_model


import sys
from PIL import Image
import io

import boto3
from django.conf import settings
from fpdf import FPDF 
from base64 import b64decode

User = get_user_model()

class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        messages = Message.last_10_messages()
        content = {
            'messages': self.messages_to_json(messages),
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        author_user = User.objects.filter(username=author)[0]
        file_name = data['filename'] if 'filename' in data else 'null'
        message = Message.objects.create(author=author_user, content=data['message'], filename=file_name)
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message),
        }
        self.send_chat_message(content)


    def messages_to_json(self, messages):
        result = []
        for message in messages:
              result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            'id':  message.id,
            'author': message.author.username,
            'message': message.content,
            'timestamp': str(message.timestamp),
            'filename': message.filename
        }

    def save_session(self, data):
        self.scope['session']['type_file'] = data['type']
        self.scope['session']['author'] = data['author']
        self.scope['session']['name'] = data['name']


    def save_file(self, data):
        with open("static/" + self.scope['session']['name'], "wb") as f:
            f.write(data)
        s3 = boto3.client('s3', region_name='eu-central-1', 
                                aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        s3.upload_file(Filename='static/' + self.scope['session']['name'], 
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME, 
                        Key='upload/' + self.scope['session']['name'])
        filename = self.scope['session']['name']
        s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.eu-central-1.amazonaws.com/upload/{filename}"
        return {"command":"new_message",
                "message": s3_url,
                "filename": self.scope['session']['name'],
                "from": self.scope['session']['author']}


    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message,
        'save_session': save_session
    }



    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']
        self.room_group_name = 'chat_%s' % self.room_name
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()


    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )


    # Receive message from WebSocket
    def receive(self, **kwargs):        
        if 'bytes_data' in kwargs.keys():
            data = self.save_file(kwargs['bytes_data'])
        else:
            data = json.loads(kwargs['text_data'])
        self.commands[data['command']](self, data)


    def send_chat_message(self, message):

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )


    def send_message(self, message):
        self.send(text_data=json.dumps(message))




    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps(message))



