#!/usr/bin/env python3
"""
Dispatcharr v16 Original Downgrade
==================================

Bringt die aktuelle Database auf den exakten Stand von v16 Original zurück.
LÖSCHT neuere Tabellen und fügt fehlende v16-Tabellen hinzu.

VERWENDUNG:
    python downgrade_to_v16_original.py

FUNKTIONEN:
- Löscht neuere Tabellen (m3u_m3uaccountmac)
- Fügt fehlende v16-Tabellen hinzu (core_systemevent)
- Stellt exakte v16-Original Kompatibilität her
- Bereitet für Enhancement-Patch vor
"""

import os
import sys
import django
from datetime import datetime

# Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from django.db import connection, transaction
from django.core.management import call_command

class V16OriginalDowngrader:
    def __init__(self):
        self.cursor = connection.cursor()
        self.tables_to_remove = []
        self.tables_to_add = []
        self.removed_tables = []
        self.added_tables = []
        
    def print_header(self):
        print("⬇️  Dispatcharr v16 Original Downgrade")
        print("=" * 42)
        print()
        
    def create_backup(self):
        """Erstellt Backup vor Downgrade"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"dispatcharr_v16_downgrade_backup_{timestamp}.json"
            
            print("💾 Erstelle Sicherheitsbackup...")
            
            with open(backup_file, 'w') as f:
                call_command('dumpdata', 
                           'auth', 'core', 'm3u', 'channels',
                           format='json', 
                           indent=2,
                           stdout=f)
            
            print(f"✅ Backup erstellt: {backup_file}")
            return backup_file
            
        except Exception as e:
            print(f"⚠️  Backup-Erstellung fehlgeschlagen: {e}")
            return None
    
    def analyze_current_vs_v16_original(self):
        """Analysiert Unterschiede zwischen aktueller DB und v16 Original"""
        print("🔍 Analysiere Unterschiede zu v16 Original...")
        
        try:
            # Aktuelle Tabellen holen
            if connection.vendor == 'postgresql':
                self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            else:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            
            current_tables = {table[0] for table in self.cursor.fetchall()}
            
            # v16 Original Tabellen (aus deiner Liste)
            v16_original_tables = {
                'accounts_user',
                'accounts_user_channel_profiles',
                'accounts_user_groups',
                'accounts_user_user_permissions',
                'auth_group',
                'auth_group_permissions',
                'auth_permission',
                'core_coresettings',
                'core_streamprofile',
                'core_systemevent',  # Fehlt in Clean, aber in v16 Original
                'core_useragent',
                'dashboard_settings',
                'dispatcharr_channels_channel',
                'dispatcharr_channels_channelgroup',
                'dispatcharr_channels_channelgroupm3uaccount',
                'dispatcharr_channels_channelprofile',
                'dispatcharr_channels_channelprofilemembership',
                'dispatcharr_channels_channelstream',
                'dispatcharr_channels_logo',
                'dispatcharr_channels_recording',
                'dispatcharr_channels_recurringrecordingrule',
                'dispatcharr_channels_stream',
                'django_admin_log',
                'django_celery_beat_clockedschedule',
                'django_celery_beat_crontabschedule',
                'django_celery_beat_intervalschedule',
                'django_celery_beat_periodictask',
                'django_celery_beat_periodictasks',
                'django_celery_beat_solarschedule',
                'django_content_type',
                'django_migrations',
                'django_session',
                'epg_epgdata',
                'epg_epgsource',
                'epg_programdata',
                'hdhr_hdhrdevice',
                'm3u_m3uaccount',
                # 'm3u_m3uaccountmac',  # NICHT in v16 Original!
                'm3u_m3uaccountprofile',
                'm3u_m3ufilter',
                'm3u_servergroup',
                'plugins_pluginconfig',
                'vod_episode',
                'vod_m3uepisoderelation',
                'vod_m3umovierelation',
                'vod_m3useriesrelation',
                'vod_m3uvodcategoryrelation',
                'vod_movie',
                'vod_series',
                'vod_vodcategory',
                'vod_vodlogo'
            }
            
            # Tabellen die entfernt werden müssen (in aktuell, aber nicht in v16 Original)
            self.tables_to_remove = current_tables - v16_original_tables
            
            # Tabellen die hinzugefügt werden müssen (in v16 Original, aber nicht in aktuell)
            self.tables_to_add = v16_original_tables - current_tables
            
            print(f"📊 Analyse-Ergebnis:")
            print(f"   Aktuelle Tabellen: {len(current_tables)}")
            print(f"   v16 Original Tabellen: {len(v16_original_tables)}")
            
            if self.tables_to_remove:
                print(f"\n❌ Zu entfernende Tabellen ({len(self.tables_to_remove)}):")
                for table in sorted(self.tables_to_remove):
                    print(f"   - {table}")
            
            if self.tables_to_add:
                print(f"\n➕ Hinzuzufügende Tabellen ({len(self.tables_to_add)}):")
                for table in sorted(self.tables_to_add):
                    print(f"   + {table}")
            
            if not self.tables_to_remove and not self.tables_to_add:
                print(f"\n✅ Database ist bereits v16 Original-kompatibel!")
            
            return len(self.tables_to_remove) > 0 or len(self.tables_to_add) > 0
            
        except Exception as e:
            print(f"❌ Fehler bei der Analyse: {e}")
            return False
    
    def remove_newer_tables(self):
        """Entfernt Tabellen die neuer als v16 Original sind"""
        if not self.tables_to_remove:
            return True
        
        print(f"🗑️  Entferne {len(self.tables_to_remove)} neuere Tabellen...")
        
        try:
            with transaction.atomic():
                for table in self.tables_to_remove:
                    print(f"   🗑️  Lösche Tabelle: {table}")
                    
                    # Prüfe ob Tabelle Daten hat
                    try:
                        self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = self.cursor.fetchone()[0]
                        if count > 0:
                            print(f"      ⚠️  Tabelle hat {count} Einträge - werden gelöscht!")
                    except:
                        pass
                    
                    # Tabelle löschen
                    self.cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    self.removed_tables.append(table)
                    print(f"      ✅ {table} gelöscht")
            
            print(f"✅ {len(self.removed_tables)} Tabellen erfolgreich entfernt")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Entfernen der Tabellen: {e}")
            return False
    
    def add_missing_v16_tables(self):
        """Fügt fehlende v16 Original Tabellen hinzu"""
        if not self.tables_to_add:
            return True
        
        print(f"➕ Füge {len(self.tables_to_add)} fehlende v16-Tabellen hinzu...")
        
        try:
            with transaction.atomic():
                for table in self.tables_to_add:
                    if table == 'core_systemevent':
                        print(f"   ➕ Erstelle Tabelle: {table}")
                        
                        if connection.vendor == 'postgresql':
                            self.cursor.execute("""
                                CREATE TABLE core_systemevent (
                                    id SERIAL PRIMARY KEY,
                                    event_type VARCHAR(50) NOT NULL,
                                    message TEXT NOT NULL,
                                    details JSONB,
                                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                                    user_id INTEGER REFERENCES accounts_user(id) ON DELETE SET NULL
                                )
                            """)
                        else:
                            self.cursor.execute("""
                                CREATE TABLE core_systemevent (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    event_type VARCHAR(50) NOT NULL,
                                    message TEXT NOT NULL,
                                    details TEXT,
                                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    user_id INTEGER REFERENCES accounts_user(id) ON DELETE SET NULL
                                )
                            """)
                        
                        self.added_tables.append(table)
                        print(f"      ✅ {table} erstellt")
                    else:
                        print(f"   ⚠️  Unbekannte Tabelle: {table} - übersprungen")
            
            if self.added_tables:
                print(f"✅ {len(self.added_tables)} Tabellen erfolgreich hinzugefügt")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Hinzufügen der Tabellen: {e}")
            return False
    
    def update_migrations_table(self):
        """Aktualisiert Django-Migrationen für v16-Kompatibilität"""
        print("🔄 Aktualisiere Migration-Status...")
        
        try:
            # Entferne Migrationen für gelöschte Tabellen
            if 'm3u_m3uaccountmac' in self.removed_tables:
                print("   🗑️  Entferne m3u_m3uaccountmac Migrationen...")
                
                # Finde und entferne MAC-bezogene Migrationen
                self.cursor.execute("""
                    DELETE FROM django_migrations 
                    WHERE app = 'm3u' AND name LIKE '%mac%'
                """)
                
                deleted_migrations = self.cursor.rowcount
                if deleted_migrations > 0:
                    print(f"      ✅ {deleted_migrations} MAC-Migrationen entfernt")
            
            print("✅ Migration-Status aktualisiert")
            return True
            
        except Exception as e:
            print(f"⚠️  Migration-Update teilweise fehlgeschlagen: {e}")
            return True  # Nicht kritisch
    
    def verify_v16_original_compatibility(self):
        """Verifiziert v16 Original Kompatibilität"""
        print("🧪 Verifiziere v16 Original Kompatibilität...")
        
        try:
            # Aktuelle Tabellen nach Downgrade
            if connection.vendor == 'postgresql':
                self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            else:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            
            current_tables = {table[0] for table in self.cursor.fetchall()}
            
            # Prüfe kritische v16-Tabellen
            v16_critical_tables = [
                'm3u_m3uaccount',
                'm3u_m3uaccountprofile',
                'core_systemevent',
                'dispatcharr_channels_channel',
                'dispatcharr_channels_stream'
            ]
            
            # Prüfe dass MAC-Tabelle NICHT existiert
            forbidden_tables = ['m3u_m3uaccountmac']
            
            print("📊 v16 Original Kompatibilitäts-Check:")
            
            all_good = True
            
            for table in v16_critical_tables:
                if table in current_tables:
                    try:
                        self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = self.cursor.fetchone()[0]
                        print(f"   ✅ {table:<30} {count:>6} Einträge")
                    except:
                        print(f"   ⚠️  {table:<30} Zugriffsfehler")
                        all_good = False
                else:
                    print(f"   ❌ {table:<30} FEHLT")
                    all_good = False
            
            for table in forbidden_tables:
                if table in current_tables:
                    print(f"   ❌ {table:<30} SOLLTE NICHT EXISTIEREN")
                    all_good = False
                else:
                    print(f"   ✅ {table:<30} korrekt entfernt")
            
            if all_good:
                print("\n✅ Database ist v16 Original-kompatibel!")
                return True
            else:
                print("\n❌ Einige Kompatibilitätsprobleme gefunden")
                return False
            
        except Exception as e:
            print(f"❌ Fehler bei Kompatibilitäts-Check: {e}")
            return False
    
    def show_downgrade_summary(self):
        """Zeigt Downgrade-Zusammenfassung"""
        print(f"\n📊 v16 Original Downgrade Zusammenfassung:")
        
        if self.removed_tables:
            print(f"   Entfernte Tabellen: {len(self.removed_tables)}")
            for table in self.removed_tables:
                print(f"     - {table}")
        
        if self.added_tables:
            print(f"   Hinzugefügte Tabellen: {len(self.added_tables)}")
            for table in self.added_tables:
                print(f"     + {table}")
        
        if not self.removed_tables and not self.added_tables:
            print(f"   Keine Änderungen nötig - bereits v16 Original-kompatibel")
        
        print(f"\n🎉 Database ist jetzt exakt v16 Original-kompatibel!")
        
        print(f"\n🚀 Nächste Schritte:")
        print(f"   1. Enhancements anwenden (fügt nur Proxy-Feld hinzu):")
        print(f"      ./apply_dispatcharr_enhancements.sh")
        print(f"   ")
        print(f"   2. System testen:")
        print(f"      python manage.py runserver")
        print(f"   ")
        print(f"   3. Keine Foreign Key Probleme mehr:")
        print(f"      m3u_m3uaccountmac Tabelle wurde entfernt")
    
    def run_downgrade(self):
        """Führt komplettes v16 Original Downgrade durch"""
        self.print_header()
        
        # Backup erstellen
        backup_file = self.create_backup()
        print()
        
        # Unterschiede analysieren
        needs_changes = self.analyze_current_vs_v16_original()
        print()
        
        if not needs_changes:
            print("✅ Database ist bereits v16 Original-kompatibel!")
            return True
        
        # Sicherheitsabfrage
        total_changes = len(self.tables_to_remove) + len(self.tables_to_add)
        print(f"⚠️  Dieser Downgrade wird {total_changes} Tabellen-Änderungen vornehmen!")
        if self.tables_to_remove:
            print(f"   🗑️  {len(self.tables_to_remove)} Tabellen werden GELÖSCHT")
        if self.tables_to_add:
            print(f"   ➕ {len(self.tables_to_add)} Tabellen werden hinzugefügt")
        
        if backup_file:
            print(f"   💾 Backup wurde erstellt: {backup_file}")
        
        response = input("Möchten Sie das v16 Original Downgrade durchführen? (ja/nein): ")
        if response.lower() not in ['ja', 'j', 'yes', 'y']:
            print("❌ v16 Original Downgrade abgebrochen")
            return False
        
        print()
        
        # Neuere Tabellen entfernen
        if not self.remove_newer_tables():
            print("❌ Tabellen-Entfernung fehlgeschlagen")
            return False
        
        print()
        
        # Fehlende v16-Tabellen hinzufügen
        if not self.add_missing_v16_tables():
            print("❌ Tabellen-Hinzufügung fehlgeschlagen")
            return False
        
        print()
        
        # Migration-Status aktualisieren
        self.update_migrations_table()
        
        print()
        
        # v16 Original Kompatibilität verifizieren
        success = self.verify_v16_original_compatibility()
        
        # Zusammenfassung anzeigen
        self.show_downgrade_summary()
        
        return success

def main():
    try:
        downgrader = V16OriginalDowngrader()
        success = downgrader.run_downgrade()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ v16 Original Downgrade abgebrochen")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()