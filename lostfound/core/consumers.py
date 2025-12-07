"""
WebSocket Consumers pour la messagerie en temps réel
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import logging

from .models import Conversation, Message, Utilisateur

logger = logging.getLogger(__name__)

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les conversations de chat en temps réel
    """
    
    async def connect(self):
        """Connexion WebSocket"""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope["user"]
        
        # Vérifier que l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Vérifier les permissions pour accéder à cette conversation
        can_access = await self.can_access_conversation()
        if not can_access:
            await self.close(code=4003)
            return
        
        # Rejoindre le groupe de conversation
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notifier la connexion aux autres participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.get_full_name(),
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        # Notifier la déconnexion aux autres participants
        if hasattr(self, 'conversation_group_name'):
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.get_full_name(),
                    'status': 'offline'
                }
            )
            
            # Quitter le groupe de conversation
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Réception d'un message du client"""
        try:
            data = json.loads(text_data)
            action = data.get('action', '')
            
            if action == 'send_message':
                await self.handle_send_message(data)
            elif action == 'mark_as_read':
                await self.handle_mark_as_read(data)
            elif action == 'typing':
                await self.handle_typing(data)
            else:
                logger.warning(f"Action non reconnue: {action}")
                
        except json.JSONDecodeError:
            logger.error("Erreur de décodage JSON")
        except Exception as e:
            logger.error(f"Erreur dans receive: {e}")
    
    async def handle_send_message(self, data):
        """Traiter l'envoi d'un message"""
        contenu = data.get('message', '').strip()
        
        if not contenu:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Le message ne peut pas être vide'
            }))
            return
        
        # Créer le message en base de données
        message = await self.create_message(contenu)
        if not message:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Erreur lors de la création du message'
            }))
            return
        
        # Diffuser le message à tous les participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'contenu': message.contenu,
                    'sender_id': message.sender.id,
                    'sender_name': message.sender.get_full_name(),
                    'sender_role': message.sender.role,
                    'receiver_id': message.receiver.id,
                    'receiver_name': message.receiver.get_full_name(),
                    'type_message': message.type_message,
                    'is_read': message.is_read,
                    'created_at': message.created_at.isoformat(),
                    'fichier_url': message.fichier.url if message.fichier else None,
                    'file_name': message.file_name,
                    'is_image': message.is_image,
                }
            }
        )
    
    async def handle_mark_as_read(self, data):
        """Marquer les messages comme lus"""
        await self.mark_messages_as_read()
        
        # Notifier les autres participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'messages_read',
                'user_id': self.user.id,
                'username': self.user.get_full_name()
            }
        )
    
    async def handle_typing(self, data):
        """Gérer l'indicateur de frappe"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )
    
    # Handlers pour les messages reçus du group
    
    async def chat_message(self, event):
        """Envoyer un message de chat au WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': event['message']
        }))
    
    async def user_status(self, event):
        """Envoyer le statut d'un utilisateur au WebSocket"""
        # Ne pas envoyer son propre statut
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'data': {
                    'user_id': event['user_id'],
                    'username': event['username'],
                    'status': event['status']
                }
            }))
    
    async def messages_read(self, event):
        """Notifier que des messages ont été lus"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'data': {
                    'user_id': event['user_id'],
                    'username': event['username']
                }
            }))
    
    async def typing_indicator(self, event):
        """Envoyer l'indicateur de frappe au WebSocket"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'data': {
                    'user_id': event['user_id'],
                    'username': event['username'],
                    'is_typing': event['is_typing']
                }
            }))
    
    # Méthodes utilitaires
    
    @database_sync_to_async
    def can_access_conversation(self):
        """Vérifier si l'utilisateur peut accéder à cette conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return (conversation.agent == self.user or 
                   conversation.declarant == self.user or
                   self.user.role == 'admin')
        except ObjectDoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, contenu):
        """Créer un message en base de données"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Déterminer le destinataire
            if self.user == conversation.agent:
                receiver = conversation.declarant
            else:
                receiver = conversation.agent
            
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                receiver=receiver,
                contenu=contenu,
                type_message='texte'
            )
            
            # Mettre à jour la date de dernière modification de la conversation
            conversation.save()
            
            return message
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du message: {e}")
            return None
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        """Marquer tous les messages non lus de cette conversation comme lus"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            messages_to_read = Message.objects.filter(
                conversation=conversation,
                receiver=self.user,
                is_read=False
            )
            
            for message in messages_to_read:
                message.mark_as_read()
                
        except Exception as e:
            logger.error(f"Erreur lors du marquage des messages comme lus: {e}")


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les notifications globales d'un utilisateur
    """
    
    async def connect(self):
        """Connexion WebSocket pour les notifications"""
        self.user = self.scope["user"]
        
        # Vérifier que l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Groupe pour les notifications de cet utilisateur
        self.notification_group_name = f'notifications_{self.user.id}'
        
        # Rejoindre le groupe de notifications
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Réception d'un message du client pour les notifications"""
        try:
            data = json.loads(text_data)
            action = data.get('action', '')
            
            if action == 'get_unread_count':
                await self.send_unread_count()
                
        except json.JSONDecodeError:
            logger.error("Erreur de décodage JSON dans NotificationConsumer")
    
    async def notification(self, event):
        """Envoyer une notification au WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def unread_count_update(self, event):
        """Envoyer la mise à jour du nombre de messages non lus"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def send_unread_count(self):
        """Envoyer le nombre de messages non lus"""
        try:
            # Compter les conversations avec des messages non lus
            if self.user.role in ['agent', 'admin']:
                conversations = Conversation.objects.filter(agent=self.user)
                unread_count = sum(conv.unread_count_for_agent for conv in conversations)
            else:
                conversations = Conversation.objects.filter(declarant=self.user)
                unread_count = sum(conv.unread_count_for_declarant for conv in conversations)
            
            self.channel_layer.group_send(
                self.notification_group_name,
                {
                    'type': 'unread_count_update',
                    'data': {'unread_count': unread_count}
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des messages non lus: {e}")