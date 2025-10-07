from django.core.management.base import BaseCommand
from apps.monitor.alert_config_parser import alert_config_parser


class Command(BaseCommand):
    help = 'Synchronize and validate alert types from configuration file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Display detailed information about alert types',
        )

    def handle(self, *args, **options):
        self.stdout.write("Synchronizing alert types from configuration...")
        
        try:
            # Reload the configuration to ensure we have the latest
            alert_config_parser.reload_config()
            
            # Get alert type choices
            alert_choices = alert_config_parser.get_alert_type_choices()
            alert_mapping = alert_config_parser.get_alert_type_mapping()
            
            if options['verbose']:
                self.stdout.write("Current alert types from configuration:")
                for value, label in alert_choices:
                    self.stdout.write(f"  - {value}: {label}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully synchronized {len(alert_choices)} alert types"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error synchronizing alert types: {str(e)}")
            )