"""Seed synthetic data: suppliers, 50 products, 100 customers, 6 months daily sales, invoices."""
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, create_tables
from backend.models.supplier import Supplier
from backend.models.product import Product
from backend.models.customer import Customer
from backend.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from backend.models.sale import Sale

CATEGORIES = ["Electronics", "Clothing", "Groceries", "Home & Kitchen", "Sports", "Beauty", "Books"]

PRODUCTS_DATA = [
    # Electronics
    ("Samsung Galaxy A54", "ELEC-001", "Electronics", 89000, 72000, "Samsung Pakistan"),
    ("iPhone 13 Cover", "ELEC-002", "Electronics", 1500, 600, "Mobile Accessories Co"),
    ("JBL Bluetooth Speaker", "ELEC-003", "Electronics", 12000, 8500, "JBL Distributor"),
    ("USB-C Charger 65W", "ELEC-004", "Electronics", 3500, 2000, "TechSupply PK"),
    ("Wireless Mouse Logitech", "ELEC-005", "Electronics", 4500, 2800, "Logitech Dealer"),
    ("Laptop Stand Aluminum", "ELEC-006", "Electronics", 2800, 1500, "TechSupply PK"),
    ("HDMI Cable 2m", "ELEC-007", "Electronics", 800, 350, "Cable World"),
    ("Power Bank 20000mAh", "ELEC-008", "Electronics", 5500, 3500, "TechSupply PK"),
    # Clothing
    ("Men's Shalwar Kameez", "CLO-001", "Clothing", 3500, 1800, "Al-Karam Textiles"),
    ("Women's Lawn Suit", "CLO-002", "Clothing", 4200, 2200, "Gul Ahmed"),
    ("Denim Jeans Men", "CLO-003", "Clothing", 2800, 1400, "Levi's Distributor"),
    ("Kids T-Shirt Pack 3", "CLO-004", "Clothing", 1200, 600, "Bonanza Textiles"),
    ("Winter Jacket Men", "CLO-005", "Clothing", 8500, 5000, "Outfitters Wholesale"),
    ("Women's Hijab Premium", "CLO-006", "Clothing", 800, 350, "Hijab House"),
    ("Sports Shoes Nike", "CLO-007", "Clothing", 12000, 8000, "Nike Pakistan"),
    # Groceries
    ("Basmati Rice 5kg", "GRO-001", "Groceries", 1200, 900, "Rice Mills PK"),
    ("Sunflower Oil 5L", "GRO-002", "Groceries", 2200, 1700, "Sufi Foods"),
    ("Nestle Milk Powder 1kg", "GRO-003", "Groceries", 1800, 1400, "Nestle Pakistan"),
    ("Whole Wheat Atta 10kg", "GRO-004", "Groceries", 1500, 1100, "Flour Mills"),
    ("Tata Salt 1kg", "GRO-005", "Groceries", 150, 100, "Tata Distributor"),
    ("Surf Excel 1kg", "GRO-006", "Groceries", 450, 300, "Unilever Pakistan"),
    ("Colgate Toothpaste 200g", "GRO-007", "Groceries", 320, 200, "Colgate Palmolive"),
    ("Dettol Soap 3pack", "GRO-008", "Groceries", 420, 280, "Reckitt Benckiser"),
    # Home & Kitchen
    ("Non-Stick Frying Pan", "HOM-001", "Home & Kitchen", 1800, 1000, "Kitchen Pro"),
    ("Pressure Cooker 5L", "HOM-002", "Home & Kitchen", 3500, 2200, "National Cookware"),
    ("Steel Water Bottle", "HOM-003", "Home & Kitchen", 700, 350, "HomeGoods PK"),
    ("Bed Sheet Set Queen", "HOM-004", "Home & Kitchen", 2500, 1400, "Chenab Textiles"),
    ("Vacuum Cleaner Anex", "HOM-005", "Home & Kitchen", 6500, 4500, "Anex Electronics"),
    ("LED Bulb Pack 5", "HOM-006", "Home & Kitchen", 850, 500, "Philips Dealer"),
    # Sports
    ("Cricket Bat Kashmir", "SPO-001", "Sports", 4500, 2800, "Sports World PK"),
    ("Football Size 5", "SPO-002", "Sports", 2200, 1400, "Nike Sports"),
    ("Yoga Mat Premium", "SPO-003", "Sports", 1800, 1000, "Fitness Pro"),
    ("Badminton Set", "SPO-004", "Sports", 1500, 900, "Sports World PK"),
    ("Protein Powder 1kg", "SPO-005", "Sports", 4800, 3200, "Nutrition Plus"),
    # Beauty
    ("Nivea Face Cream", "BEA-001", "Beauty", 650, 400, "Beiersdorf PK"),
    ("L'Oreal Shampoo 400ml", "BEA-002", "Beauty", 950, 600, "L'Oreal Pakistan"),
    ("Lipstick Set 6colors", "BEA-003", "Beauty", 1200, 700, "Color Studio"),
    ("Revlon Foundation", "BEA-004", "Beauty", 1800, 1100, "Revlon Distributor"),
    ("Perfume Men 100ml", "BEA-005", "Beauty", 3500, 2000, "Fragrance House"),
    # Books
    ("Python Programming Book", "BOO-001", "Books", 1500, 800, "Paramount Books"),
    ("Urdu Novel Aangan", "BOO-002", "Books", 600, 300, "Sang-e-Meel"),
    ("Class 10 Physics Book", "BOO-003", "Books", 450, 250, "Oxford Pakistan"),
    ("Business Management", "BOO-004", "Books", 1200, 700, "Paramount Books"),
    ("Children Story Pack 5", "BOO-005", "Books", 1800, 1000, "Ferozesons"),
    # Extra Electronics
    ("Smart Watch Xiaomi", "ELEC-009", "Electronics", 18000, 13000, "Xiaomi Pakistan"),
    ("Earbuds TWS Budget", "ELEC-010", "Electronics", 2500, 1400, "Mobile Accessories Co"),
    ("Keyboard Mechanical", "ELEC-011", "Electronics", 8500, 5500, "TechSupply PK"),
    ("Webcam HD 1080p", "ELEC-012", "Electronics", 6000, 3800, "Logitech Dealer"),
    ("SSD 256GB External", "ELEC-013", "Electronics", 9500, 6500, "TechSupply PK"),
    ("Router TP-Link WiFi6", "ELEC-014", "Electronics", 14000, 10000, "TP-Link Dealer"),
]

# (name, email, phone, contact_person) — names must match product supplier text exactly
SUPPLIERS_DATA = [
    ("Samsung Pakistan",      "orders@samsung.com.pk",        "+92-21-3456-7890", "Tariq Mehmood"),
    ("Mobile Accessories Co", "orders@mobileaccessories.pk",  "+92-42-3567-8901", "Bilal Rafiq"),
    ("JBL Distributor",       "procurement@jbldistributor.pk","+92-51-2345-6789", "Kamran Shah"),
    ("TechSupply PK",         "orders@techsupplypk.com",      "+92-21-4567-8901", "Hassan Raza"),
    ("Logitech Dealer",       "logitech@pkdealer.com",        "+92-42-6789-0123", "Usman Ali"),
    ("Cable World",           "cableworld@gmail.com",         "+92-300-1234567",  "Asif Khan"),
    ("Al-Karam Textiles",     "procurement@alkaram.com",      "+92-21-3213-4567", "Zahid Hussain"),
    ("Gul Ahmed",             "orders@gulahmed.com",          "+92-21-3234-5678", "Faisal Ahmed"),
    ("Levi's Distributor",    "levis@pkdistributor.com",      "+92-42-3890-1234", "Saad Nawaz"),
    ("Bonanza Textiles",      "bonanza@textiles.pk",          "+92-42-3901-2345", "Imran Sheikh"),
    ("Outfitters Wholesale",  "wholesale@outfitters.pk",      "+92-51-3012-3456", "Rizwan Butt"),
    ("Hijab House",           "hijabhouse@gmail.com",         "+92-333-2345678",  "Amina Siddiqui"),
    ("Nike Pakistan",         "nike@pkdistributor.com",       "+92-21-4123-4567", "Waqas Javed"),
    ("Nike Sports",           "nikesports@pkdistributor.com", "+92-21-4124-5678", "Waqas Javed"),
    ("Rice Mills PK",         "ricemills@gmail.com",          "+92-61-3456-7890", "Ghulam Farid"),
    ("Sufi Foods",            "sufifoods@gmail.com",          "+92-42-3567-8902", "Arif Sufi"),
    ("Nestle Pakistan",       "nestle@nestle.pk",             "+92-21-5123-4567", "Sadia Malik"),
    ("Flour Mills",           "flourmills@gmail.com",         "+92-61-4567-8901", "Hamid Rana"),
    ("Tata Distributor",      "tata@pkdistributor.com",       "+92-21-3678-9012", "Raj Kumar"),
    ("Unilever Pakistan",     "unilever@unilever.pk",         "+92-21-5234-5678", "Ayesha Noor"),
    ("Colgate Palmolive",     "colgate@palmolive.pk",         "+92-21-5345-6789", "Naeem Qureshi"),
    ("Reckitt Benckiser",     "reckitt@reckitt.pk",           "+92-21-5456-7890", "Omar Farhan"),
    ("Kitchen Pro",           "kitchenpro@gmail.com",         "+92-42-3789-0123", "Salma Bibi"),
    ("National Cookware",     "national@cookware.pk",         "+92-42-3890-1235", "Tariq Aziz"),
    ("HomeGoods PK",          "homegoods@pk.com",             "+92-300-3456789",  "Nadia Bashir"),
    ("Chenab Textiles",       "chenab@textiles.pk",           "+92-47-3901-2346", "Shahid Latif"),
    ("Anex Electronics",      "anex@electronics.pk",          "+92-42-4012-3457", "Pervez Iqbal"),
    ("Philips Dealer",        "philips@pkdealer.com",         "+92-21-4234-5679", "Zubair Ahmad"),
    ("Sports World PK",       "sportsworldpk@gmail.com",      "+92-42-3456-7891", "Junaid Akram"),
    ("Fitness Pro",           "fitnesspro@gmail.com",         "+92-300-4567890",  "Adnan Malik"),
    ("Nutrition Plus",        "nutritionplus@gmail.com",      "+92-321-5678901",  "Ahsan Ali"),
    ("Beiersdorf PK",         "beiersdorf@pk.com",            "+92-21-5678-9013", "Hina Asif"),
    ("L'Oreal Pakistan",      "loreal@loreal.pk",             "+92-21-5789-0124", "Mehwish Tariq"),
    ("Color Studio",          "colorstudio@gmail.com",        "+92-300-6789012",  "Sana Riaz"),
    ("Revlon Distributor",    "revlon@pkdistributor.com",     "+92-42-3901-2347", "Amna Zulfiqar"),
    ("Fragrance House",       "fragrancehouse@gmail.com",     "+92-300-7890123",  "Khalid Mehmood"),
    ("Paramount Books",       "paramount@books.pk",           "+92-42-3576-8901", "Irfan Siddiqui"),
    ("Sang-e-Meel",           "sangemeel@gmail.com",          "+92-42-3723-4567", "Naseem Akhtar"),
    ("Oxford Pakistan",       "oxford@oxford.pk",             "+92-42-3834-5678", "Rabia Nawaz"),
    ("Ferozesons",            "ferozesons@gmail.com",         "+92-42-3945-6789", "Farhan Awan"),
    ("Xiaomi Pakistan",       "xiaomi@xiaomi.pk",             "+92-21-4345-6789", "Li Wei"),
    ("TP-Link Dealer",        "tplink@pkdealer.com",          "+92-21-4456-7890", "Zeeshan Haider"),
]

CUSTOMER_NAMES = [
    "Ahmed Ali", "Fatima Khan", "Muhammad Hassan", "Ayesha Malik", "Usman Raza",
    "Zainab Ahmed", "Ali Hassan", "Maryam Siddiqui", "Omar Farooq", "Hina Akhtar",
    "Bilal Chaudhry", "Sana Tariq", "Kamran Mirza", "Nadia Hussain", "Asad Butt",
    "Rabia Nawaz", "Imran Sheikh", "Amna Qureshi", "Faisal Javed", "Sobia Latif",
    "Tariq Mahmood", "Rida Anwar", "Waseem Baig", "Madiha Zahid", "Shahid Iqbal",
    "Uzma Rehman", "Aamir Zafar", "Sadaf Noor", "Junaid Aslam", "Samina Parveen",
    "Kashif Mehmood", "Huma Shafi", "Nabeel Gul", "Mehwish Rana", "Shoaib Dar",
    "Lubna Saeed", "Talha Chaudhry", "Sadia Malik", "Hamza Abbasi", "Naila Asghar",
    "Rizwan Haider", "Bushra Saleem", "Irfan Khan", "Zara Gillani", "Ahsan Nasir",
    "Farida Akram", "Nadeem Awan", "Tooba Rafiq", "Salman Bhatti", "Amira Khalid",
    "Waqas Ashraf", "Aliya Shakeel", "Adnan Sattar", "Rubina Tanveer", "Moeen Ansari",
    "Shazia Ehsan", "Haris Qazi", "Nargis Bano", "Sajid Hussain", "Fariha Memon",
    "Nawaz Bhutto", "Sumbul Amjad", "Basit Ali", "Maham Farhan", "Asim Rauf",
    "Kiran Liaquat", "Ghulam Mustafa", "Saima Yousaf", "Danish Kamal", "Laila Zeb",
    "Raza Naqvi", "Sumaira Bashir", "Khurram Nisar", "Hira Ilyas", "Farrukh Usman",
    "Nazia Batool", "Jamshed Mirza", "Ayesha Nabi", "Babar Azam", "Sumera Ishaq",
    "Zulfiqar Ali", "Mariam Fazal", "Tahir Nawaz", "Komal Arshad", "Ijaz Ahmad",
    "Benazir Shah", "Amir Hamza", "Shela Hafeez", "Murad Wali", "Naeema Gul",
    "Saleem Akhtar", "Tabassum Arif", "Aslam Khan", "Fozia Aziz", "Rauf Butt",
    "Ambreen Saeed", "Zaheer Abbas", "Muniba Mazari", "Pervaiz Iqbal", "Shehnaz Mir",
]


def seed_database():
    create_tables()
    db = SessionLocal()

    try:
        # Clear existing data
        db.query(Sale).delete()
        db.query(InvoiceItem).delete()
        db.query(Invoice).delete()
        db.query(Customer).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.commit()

        # Seed suppliers
        for name, email, phone, contact in SUPPLIERS_DATA:
            db.add(Supplier(name=name, email=email, phone=phone, contact_person=contact))
        db.commit()
        print(f"Seeded {len(SUPPLIERS_DATA)} suppliers")

        # Seed products
        products = []
        for i, (name, sku, cat, price, cost, supplier) in enumerate(PRODUCTS_DATA):
            qty = random.randint(5, 200)
            p = Product(
                name=name, sku=sku, category=cat,
                price=price, cost_price=cost,
                quantity=qty,
                reorder_level=random.choice([5, 10, 15, 20]),
                supplier=supplier,
            )
            db.add(p)
            products.append(p)
        db.commit()
        print(f"Seeded {len(products)} products")

        # Seed customers
        customers = []
        for i, full_name in enumerate(CUSTOMER_NAMES):
            first = full_name.split()[0].lower()
            c = Customer(
                name=full_name,
                email=f"{first}{i+1}@example.com",
                phone=f"03{random.randint(100000000, 399999999)}",
                address=f"House {random.randint(1,500)}, Street {random.randint(1,50)}, {random.choice(['Lahore','Karachi','Islamabad','Peshawar','Quetta'])}",
                loyalty_points=random.randint(0, 5000),
                total_spent=0.0,
            )
            db.add(c)
            customers.append(c)
        db.commit()
        print(f"Seeded {len(customers)} customers")

        # Seed 6 months daily sales
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        sale_records = []
        invoice_num = 1000

        current = start_date
        while current <= end_date:
            daily_txns = random.randint(5, 25)
            for _ in range(daily_txns):
                customer = random.choice(customers)
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))

                total = 0.0
                items_data = []
                for prod in selected_products:
                    qty = random.randint(1, 5)
                    subtotal = qty * prod.price
                    total += subtotal
                    items_data.append((prod, qty, subtotal))

                    # Record individual sale
                    profit = qty * (prod.price - prod.cost_price)
                    sale = Sale(
                        product_id=prod.id,
                        quantity_sold=qty,
                        revenue=subtotal,
                        profit=profit,
                        sale_date=current,
                        category=prod.category,
                    )
                    db.add(sale)
                    sale_records.append(sale)

                discount = random.choice([0, 0, 0, total * 0.05, total * 0.10])
                tax = total * 0.17  # 17% GST
                net = total - discount + tax

                inv = Invoice(
                    invoice_number=f"INV-{invoice_num:06d}",
                    customer_id=customer.id,
                    total_amount=total,
                    discount=discount,
                    tax=tax,
                    net_amount=net,
                    status=random.choices(
                        [InvoiceStatus.paid, InvoiceStatus.pending, InvoiceStatus.cancelled],
                        weights=[85, 10, 5]
                    )[0],
                    payment_method=random.choice(["Cash", "Card", "EasyPaisa", "JazzCash", "Bank Transfer"]),
                    created_at=current,
                )
                db.add(inv)
                db.flush()

                for prod, qty, subtotal in items_data:
                    ii = InvoiceItem(
                        invoice_id=inv.id,
                        product_id=prod.id,
                        quantity=qty,
                        unit_price=prod.price,
                        subtotal=subtotal,
                    )
                    db.add(ii)

                # Update customer total spent
                customer.total_spent += net
                invoice_num += 1

            current += timedelta(days=1)

        db.commit()
        print(f"Seeded {len(sale_records)} sale records across 6 months")
        print(f"Seeded {invoice_num - 1000} invoices")
        print("Database seeding complete!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
