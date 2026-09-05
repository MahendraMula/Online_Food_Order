class DjangoFrameworkRouter:
    """
    Database router that controls database operations for Django framework models
    (auth, contenttypes, sessions, admin) versus application domain models.
    """
    route_app_labels = {'auth', 'contenttypes', 'sessions', 'admin'}

    def db_for_read(self, model, **hints):
        """
        Direct read queries for framework models to 'django_database'.
        Direct all other application models to 'default'.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'django_database'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Direct write queries for framework models to 'django_database'.
        Direct all other application models to 'default'.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'django_database'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between models across databases (e.g. Order in default to User in django_database).
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the framework apps only appear in 'django_database',
        and domain apps only appear in 'default'.
        """
        if app_label in self.route_app_labels:
            return db == 'django_database'
        return db == 'default'
