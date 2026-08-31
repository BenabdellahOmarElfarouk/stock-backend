from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import Store, User
from accounts.serializers import RegisterSerializer
from catalog.models import Article, Category, Unit
from inventory.models import Stock
from parties.models import Customer, Supplier


class Command(BaseCommand):
    help = "Crée un compte démo quincaillerie (admin / admin123)"

    def handle(self, *args, **options):
        if not User.objects.filter(username="owner").exists():
            User.objects.create_user(
                username="owner",
                password="owner123",
                first_name="Éditeur",
                last_name="Plateforme",
                is_platform_admin=True,
                is_staff=True,
                organisation=None,
            )
            self.stdout.write("Compte éditeur créé : owner / owner123")

        if User.objects.filter(username="admin").exists():
            self.stdout.write("Le compte admin existe déjà.")
            return

        serializer = RegisterSerializer(
            data={
                "organisation_name": "Quincaillerie El Nour",
                "trade_name": "El Nour",
                "city": "Alger",
                "username": "admin",
                "password": "admin123",
                "first_name": "Karim",
                "last_name": "Benali",
                "email": "admin@elnour.dz",
                "phone": "0550 00 00 00",
            }
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        org = user.organisation
        store = Store.objects.get(organisation=org, is_default=True)

        User.objects.create_user(
            username="vendeur",
            password="vendeur123",
            first_name="Sara",
            last_name="Amrani",
            organisation=org,
            store=store,
            role=User.Role.CASHIER,
        )

        unit_pce = Unit.objects.get(organisation=org, symbol="pce")
        unit_m = Unit.objects.get(organisation=org, symbol="m")
        unit_kg = Unit.objects.get(organisation=org, symbol="kg")
        vis = Category.objects.get(organisation=org, name="Vis & boulons")
        outils = Category.objects.get(organisation=org, name="Outils à main")
        tubes = Category.objects.get(organisation=org, name="Tubes & raccords")

        samples = [
            ("VIS-001", "6130000000011", "Vis à bois 4x40 (boîte 200)", "Spax", vis, unit_pce, 180, 280, 10, 24),
            ("VIS-002", "6130000000028", "Cheville nylon 8mm (sachet 50)", "Fischer", vis, unit_pce, 90, 160, 8, 5),
            ("OUT-010", "6130000000103", "Marteau arrache-clous 500g", "Stanley", outils, unit_pce, 850, 1450, 3, 7),
            ("OUT-011", "6130000000110", "Tournevis cruciforme PH2", "Facom", outils, unit_pce, 220, 390, 4, 12),
            ("PLO-020", "6130000000202", "Tube PVC Ø32 — 3m", "Nicoll", tubes, unit_m, 310, 520, 15, 40),
            ("PLO-021", "6130000000219", "Coude PVC 90° Ø32", "Nicoll", tubes, unit_pce, 45, 85, 20, 60),
            ("ELE-030", "6130000000301", "Câble électrique 2.5mm²", "Nexans", None, unit_m, 95, 160, 50, 120),
            ("PEI-040", "6130000000400", "Peinture acrylique blanc 10L", "ENAP", None, unit_pce, 2800, 4200, 4, 9),
        ]
        for sku, barcode, name, brand, cat, unit, buy, sell, mini, qty in samples:
            article = Article.objects.create(
                organisation=org,
                sku=sku,
                barcode=barcode,
                name=name,
                brand=brand,
                category=cat,
                unit=unit,
                purchase_price=Decimal(buy),
                sale_price=Decimal(sell),
                min_stock=Decimal(mini),
                created_by=user,
            )
            Stock.objects.create(article=article, store=store, quantity=Decimal(qty))

        Customer.objects.create(
            organisation=org, name="Client passage", city="Alger", phone=""
        )
        Customer.objects.create(
            organisation=org,
            name="EURL Bâtiment Atlas",
            phone="023 11 22 33",
            city="Alger",
            nif="000123456",
        )
        Supplier.objects.create(
            organisation=org,
            name="Grossiste Fer & Métal",
            contact_name="M. Haddad",
            phone="0561 44 55 66",
            city="Rouiba",
        )
        Supplier.objects.create(
            organisation=org,
            name="Distri-Outillage",
            contact_name="Mme. Khelifi",
            phone="0555 77 88 99",
            city="Oran",
        )

        self.stdout.write(self.style.SUCCESS("Compte démo prêt : admin / admin123"))
