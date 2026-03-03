# Generated manually on 2025-12-02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_structure_locale_to_user'),
    ]

    operations = [
        # Créer la table de conversation pour le chat
        # migrations.RunSQL("""
        #     CREATE TABLE "core_conversation_chat" (
        #         "id" serial NOT NULL PRIMARY KEY,
        #         "created_at" timestamp with time zone NOT NULL,
        #         "updated_at" timestamp with time zone NOT NULL,
        #         "signalement_id" bigint NULL REFERENCES "core_declaration" ("id") DEFERRABLE INITIALLY DEFERRED,
        #         "agent_id" bigint NULL REFERENCES "core_utilisateur" ("id") DEFERRABLE INITIALLY DEFERRED,
        #         "declarant_id" bigint NULL REFERENCES "core_utilisateur" ("id") DEFERRABLE INITIALLY DEFERRED
        #     );
        # """, reverse_sql='DROP TABLE "core_conversation_chat";'),
        
        # Créer la table de messages pour le chat
        # migrations.RunSQL("""
        #     CREATE TABLE "core_message_chat" (
        #         "id" serial NOT NULL PRIMARY KEY,
        #         "contenu" text NOT NULL,
        #         "fichier" varchar(100) NULL,
        #         "type_message" varchar(10) NOT NULL,
        #         "is_read" boolean NOT NULL,
        #         "created_at" timestamp with time zone NOT NULL,
        #         "read_at" timestamp with time zone NULL,
        #         "conversation_id" bigint NOT NULL REFERENCES "core_conversation_chat" ("id") DEFERRABLE INITIALLY DEFERRED,
        #         "sender_id" bigint NULL REFERENCES "core_utilisateur" ("id") DEFERRABLE INITIALLY DEFERRED,
        #         "receiver_id" bigint NULL REFERENCES "core_utilisateur" ("id") DEFERRABLE INITIALLY DEFERRED
        #     );
        # """, reverse_sql='DROP TABLE "core_message_chat";'),
        
        # Créer les index
        migrations.RunSQL("""
            CREATE INDEX "core_conversation_chat_signalement_id_idx" ON "core_conversation_chat" ("signalement_id");
            CREATE INDEX "core_conversation_chat_agent_id_idx" ON "core_conversation_chat" ("agent_id");
            CREATE INDEX "core_conversation_chat_declarant_id_idx" ON "core_conversation_chat" ("declarant_id");
            CREATE INDEX "core_message_chat_conversation_id_idx" ON "core_message_chat" ("conversation_id");
            CREATE INDEX "core_message_chat_sender_id_idx" ON "core_message_chat" ("sender_id");
            CREATE INDEX "core_message_chat_receiver_id_idx" ON "core_message_chat" ("receiver_id");
        """, reverse_sql=''),
    ]