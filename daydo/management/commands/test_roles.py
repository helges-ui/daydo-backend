"""
Management command to test the DayDo models.
This command creates sample data to verify the role system works correctly.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from daydo.models import Family, ChildProfile, ChildUserPermissions

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the DayDo role system by creating sample data'

    def handle(self, *args, **options):
        self.stdout.write('Testing DayDo role system...')
        
        # Create a test family
        family, created = Family.objects.get_or_create(
            name="The Test Family",
            defaults={'name': 'The Test Family'}
        )
        
        if created:
            self.stdout.write(f'Created family: {family.name}')
        else:
            self.stdout.write(f'Using existing family: {family.name}')
        
        # Create a parent user
        parent, created = User.objects.get_or_create(
            username='test_parent',
            defaults={
                'email': 'parent@test.com',
                'first_name': 'Test',
                'last_name': 'Parent',
                'family': family,
                'role': 'PARENT'
            }
        )
        
        if created:
            parent.set_password('testpass123')
            parent.save()
            self.stdout.write(f'Created parent user: {parent.username}')
        else:
            self.stdout.write(f'Using existing parent: {parent.username}')
        
        # Create a child profile (CHILD_VIEW)
        child_profile, created = ChildProfile.objects.get_or_create(
            first_name='Test',
            last_name='Child',
            family=family,
            defaults={
                'manager': parent,
                'is_view_only': True,
                'avatar': 'child'
            }
        )
        
        if created:
            self.stdout.write(f'Created child profile: {child_profile.get_display_name()}')
        else:
            self.stdout.write(f'Using existing child profile: {child_profile.get_display_name()}')
        
        # Convert to CHILD_USER
        if child_profile.is_view_only:
            try:
                child_user = child_profile.create_login_account(
                    username='test_child',
                    password='testpass123'
                )
                self.stdout.write(f'Created child user account: {child_user.username}')
                
                # Check permissions
                permissions = child_user.childuserpermissions
                self.stdout.write(f'Child user permissions created: {permissions}')
                
            except ValueError as e:
                self.stdout.write(f'Error creating child user: {e}')
        
        # Test role-based methods
        self.stdout.write('\n--- Role Testing ---')
        self.stdout.write(f'Parent can manage family: {parent.can_manage_family()}')
        self.stdout.write(f'Parent can assign tasks: {parent.can_assign_tasks()}')
        self.stdout.write(f'Parent is parent: {parent.is_parent}')
        
        if hasattr(parent, 'child_profile') and parent.child_profile:
            child_user = parent.child_profile.linked_user
            if child_user:
                self.stdout.write(f'Child user is child user: {child_user.is_child_user}')
                self.stdout.write(f'Child user can manage family: {child_user.can_manage_family()}')
        
        self.stdout.write('\n--- Family Summary ---')
        self.stdout.write(f'Family: {family.name}')
        self.stdout.write(f'Members: {family.members.count()}')
        self.stdout.write(f'Child Profiles: {family.child_profiles.count()}')
        
        self.stdout.write('\nDayDo role system test completed successfully!')
