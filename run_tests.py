import os
import sys
import django
from django.test.utils import get_runner
from django.conf import settings

if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dbms_project.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)
    failures = test_runner.run_tests(['accounts.tests', 'restaurants.tests', 'orders.tests'])
    sys.exit(bool(failures))
