from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import CustomerProfile
from accounts.forms import CustomerSignupForm

class AccountsModelAndFormTests(TestCase):
    databases = '__all__'

    def test_customer_profile_creation(self):
        user = User.objects.create_user(username='johndoe', password='password123')
        profile = CustomerProfile.objects.create(user=user, phone='+1 555-0100', address='123 Main St')
        self.assertEqual(profile.user.username, 'johndoe')
        self.assertEqual(str(profile), 'johndoe')

    def test_signup_form_validation_passwords_match(self):
        form_data = {
            'username': 'alice',
            'email': 'alice@example.com',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'phone': '+1 555-0111',
            'address': '456 Elm St',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        form = CustomerSignupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_signup_form_validation_passwords_mismatch(self):
        form_data = {
            'username': 'bob',
            'email': 'bob@example.com',
            'phone': '+1 555-0122',
            'address': '789 Oak St',
            'password': 'PasswordA',
            'confirm_password': 'PasswordB'
        }
        form = CustomerSignupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_signup_form_invalid_phone(self):
        form_data = {
            'username': 'charlie',
            'email': 'charlie@example.com',
            'phone': '123',  # Too short
            'address': '789 Oak St',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        form = CustomerSignupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_signup_form_invalid_address(self):
        form_data = {
            'username': 'david',
            'email': 'david@example.com',
            'phone': '+1 555-0199',
            'address': 'abc',  # Too short (< 5 chars)
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        form = CustomerSignupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)

class AccountsViewTests(TestCase):
    databases = '__all__'

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        self.profile = CustomerProfile.objects.create(user=self.user, phone='+1 555-0199', address='100 Pine St')

    def test_signup_view_post(self):
        resp = self.client.post('/accounts/signup/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+1 555-0200',
            'address': '200 Maple St',
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(CustomerProfile.objects.filter(phone='+1 555-0200').exists())

    def test_profile_view_update(self):
        self.client.force_login(self.user)
        resp = self.client.post('/accounts/profile/', {
            'first_name': 'Johnny',
            'last_name': 'Doe',
            'email': 'johnny@example.com',
            'phone': '+1 555-9999',
            'address': '999 New Address Blvd'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Johnny')
        self.assertEqual(self.profile.phone, '+1 555-9999')
        self.assertEqual(self.profile.address, '999 New Address Blvd')

    def test_profile_view_invalid_phone(self):
        self.client.force_login(self.user)
        resp = self.client.post('/accounts/profile/', {
            'first_name': 'Johnny',
            'last_name': 'Doe',
            'email': 'johnny@example.com',
            'phone': '12',  # Invalid phone
            'address': '999 New Address Blvd'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Please enter a valid phone number')
