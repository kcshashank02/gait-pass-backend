import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.user import User
from datetime import datetime
import bcrypt


async def create_first_admin():
    """Create the very first admin user in the database"""
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print(f"✅ Connected to MongoDB (Database: {settings.DATABASE_NAME})")
        
        user_model = User(db)
        
        # Admin credentials
        admin_data = {
            "email": "admin@gaitpass.com",
            "password": "Admin123!",  # ✅ Your preferred password
            "first_name": "System",
            "last_name": "Administrator",
            "phone": "9999999999",
            "date_of_birth": "1990-01-01",
            "role": "admin"
        }
        
        # Check if admin already exists
        existing_admin = await db.users.find_one({"email": admin_data["email"]})
        if existing_admin:
            print(f"\n⚠️  Admin user already exists!")
            print(f"📧 Email: {existing_admin['email']}")
            print(f"🆔 ID: {existing_admin['_id']}")
            print(f"\n💡 If you need to reset the password, delete this user from MongoDB and run again.")
            return
        
        # Hash password manually (bcrypt)
        hashed_password = bcrypt.hashpw(
            admin_data["password"].encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create admin user document manually (no wallet for admin)
        admin_user_doc = {
            "email": admin_data["email"],
            "password": hashed_password,
            "first_name": admin_data["first_name"],
            "last_name": admin_data["last_name"],
            "phone": admin_data["phone"],
            "date_of_birth": admin_data["date_of_birth"],
            "role": "admin",  # ✅ Admin role
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert directly into database
        result = await db.users.insert_one(admin_user_doc)
        
        print("\n" + "="*60)
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"📧 Email:    admin@gaitpass.com")
        print(f"🔑 Password: Admin123!")
        print(f"👤 Name:     System Administrator")
        print(f"📱 Phone:    9999999999")
        print(f"🎭 Role:     admin")
        print(f"🆔 ID:       {result.inserted_id}")
        print("="*60)
        print("\n⚠️  IMPORTANT NOTES:")
        print("   • No wallet created for admin (admins don't need wallets)")
        print("   • Use /api/auth/login endpoint to get access token")
        print("   • Change password after first login using /api/auth/change-password")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()
        print("🔌 Database connection closed\n")


if __name__ == "__main__":
    print("\n🚀 GaitPass Admin User Creation Script")
    print("="*60 + "\n")
    asyncio.run(create_first_admin())
