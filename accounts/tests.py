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

    def test_signup_view_get(self):
        resp = self.client.get('/accounts/signup/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'form')

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

    def test_signup_view_authenticated_redirect(self):
        self.client.force_login(self.user)
        resp = self.client.get('/accounts/signup/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/')

    def test_login_view_get(self):
        resp = self.client.get('/accounts/login/')
        self.assertEqual(resp.status_code, 200)

    def test_login_view_post_success(self):
        resp = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'password123'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['user'].is_authenticated)

    def test_login_view_post_invalid(self):
        resp = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['user'].is_authenticated)

    def test_logout_view_get(self):
        self.client.force_login(self.user)
        resp = self.client.get('/accounts/logout/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['user'].is_authenticated)

    def test_logout_view_post(self):
        self.client.force_login(self.user)
        resp = self.client.post('/accounts/logout/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['user'].is_authenticated)

    def test_profile_view_get_authenticated(self):
        self.client.force_login(self.user)
        resp = self.client.get('/accounts/profile/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '100 Pine St')

    def test_profile_view_get_unauthenticated(self):
        resp = self.client.get('/accounts/profile/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

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

    def test_profile_view_invalid_address(self):
        self.client.force_login(self.user)
        resp = self.client.post('/accounts/profile/', {
            'first_name': 'Johnny',
            'last_name': 'Doe',
            'email': 'johnny@example.com',
            'phone': '+1 555-9999',
            'address': 'abc'  # Invalid address (< 5 chars)
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Address must be at least 5 characters long')
