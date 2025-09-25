import time
from django.core.management.base import BaseCommand
from whatsapp_connector.models import EvolutionInstance


class Command(BaseCommand):
    help = 'Update connection info for Evolution instances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--instance',
            type=str,
            help='Update specific instance by name'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all instances'
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Watch for changes and update continuously'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Interval in seconds for watch mode (default: 30)'
        )

    def handle(self, *args, **options):
        if options['watch']:
            self.watch_instances(options['interval'])
        elif options['all']:
            self.update_all_instances()
        elif options['instance']:
            self.update_single_instance(options['instance'])
        else:
            self.stdout.write(
                self.style.ERROR('Use --all, --instance <name>, or --watch')
            )

    def update_single_instance(self, instance_name):
        try:
            instance = EvolutionInstance.objects.get(name=instance_name)
            self.stdout.write(f'Updating instance: {instance.name}')
            result = instance.fetch_and_update_connection_info()
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Instance {instance.name} updated successfully')
                )
                self.show_instance_info(instance)
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Instance {instance.name} update failed')
                )
        except EvolutionInstance.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Instance "{instance_name}" not found')
            )

    def update_all_instances(self):
        instances = EvolutionInstance.objects.all()
        self.stdout.write(f'Updating {instances.count()} instances...')

        for instance in instances:
            self.stdout.write(f'Updating: {instance.name}')
            result = instance.fetch_and_update_connection_info()
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {instance.name} updated')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ {instance.name} failed to update')
                )

    def watch_instances(self, interval):
        self.stdout.write(f'👀 Watching instances every {interval} seconds...')
        self.stdout.write('Press Ctrl+C to stop')

        try:
            while True:
                self.update_all_instances()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write('\n🛑 Stopped watching')

    def show_instance_info(self, instance):
        self.stdout.write(f'  📱 Phone: {instance.phone_number or "Not set"}')
        self.stdout.write(f'  👤 Profile: {instance.profile_name or "Not set"}')
        self.stdout.write(f'  🔗 Status: {instance.get_status_display()}')
        if instance.profile_pic_url:
            self.stdout.write(f'  📸 Profile pic: Set')