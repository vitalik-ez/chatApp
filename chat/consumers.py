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
#from django.core.files.uploadedfile import InMemoryUploadedFile


User = get_user_model()
class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        print("Data in fetch", data)
        messages = Message.last_10_messages()
        content = {
            'messages': self.messages_to_json(messages),
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        author_user = User.objects.filter(username=author)[0]
        message = Message.objects.create(author=author_user, content=data['message'])
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
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
        }



    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }



    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.user = self.scope['user']
        print("user", self.user)
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
    def receive(self, *args, **kwargs):
        print("list", args)
        print(kwargs.keys())
        #if 'text_data' in kwargs.keys():
        #    print(kwargs['text_data'])

        
        if 'bytes_data' in kwargs['text_data']:
            print(kwargs['text_data'])

            #image
            stream = io.BytesIO(kwargs['text_data']['bytes_data'])
            image = Image.open(stream).convert("RGBA")
            image.save("static/foto.png")
            stream.close()


            s3 = boto3.client('s3', region_name='eu-central-1', 
                                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
                                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            s3.upload_file(Filename='static/foto.png', Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key='upload/newfile.png')
            filename = 'newfile.png'
            s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.eu-central-1.amazonaws.com/upload/{filename}"
            #kwargs['text_data'] = json.dumps({"command":"new_message","message": s3_url,"from":"admin"})
            data = {"command":"new_message","message": s3_url,"from":"admin"}
            #print(kwargs['bytes_data'].decode("utf-8"))
        else:
            data = json.loads(kwargs['text_data'])


        #self.commands[data['command']](self, data)


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