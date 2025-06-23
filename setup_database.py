import sqlite3
import os

def create_database():
    """Create the EyeKnow objects database with custom and COCO objects"""
    
    db_path = 'eyeknow_objects.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ Removed existing database")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create objects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("📋 Creating database tables...")
    
    # Your 10 custom objects from the thesis (starting from class_id 1000)
    custom_objects = [
        (1000, "20 Peso Coin", "Philippine 20 peso coin", "currency"),
        (1001, "20 Peso Paper", "Philippine 20 peso paper bill", "currency"),
        (1002, "Alcohol Spray", "Hand sanitizer spray bottle", "hygiene"),
        (1003, "Banana", "Fresh banana fruit", "food"),
        (1004, "Fan Switch", "Electric fan control switch", "electronics"),
        (1005, "Key", "Door or house key", "tools"),
        (1006, "Paracetamol", "Paracetamol medicine tablet/bottle", "medicine"),
        (1007, "Sunglasses", "UV protection sunglasses", "accessories"),
        (1008, "Umbrella", "Rain protection umbrella", "accessories"),
        (1009, "Water Bottle", "Drinking water bottle", "containers"),
    ]
    
    # Common COCO objects (for pretrained YOLOv8 model)
    coco_objects = [
        (0, "person", "Human person", "people"),
        (1, "bicycle", "Bicycle vehicle", "vehicles"),
        (2, "car", "Motor vehicle car", "vehicles"),
        (3, "motorcycle", "Motorcycle vehicle", "vehicles"),
        (5, "bus", "Public transportation bus", "vehicles"),
        (6, "train", "Railway train", "vehicles"),
        (7, "truck", "Truck vehicle", "vehicles"),
        (9, "traffic light", "Traffic control light", "infrastructure"),
        (11, "stop sign", "Traffic stop sign", "infrastructure"),
        (39, "bottle", "Bottle container", "containers"),
        (40, "wine glass", "Wine drinking glass", "containers"),
        (41, "cup", "Drinking cup", "containers"),
        (42, "fork", "Eating utensil fork", "utensils"),
        (43, "knife", "Cutting knife", "utensils"),
        (44, "spoon", "Eating spoon", "utensils"),
        (45, "bowl", "Food bowl", "containers"),
        (46, "banana", "Banana fruit", "food"),
        (47, "apple", "Apple fruit", "food"),
        (48, "sandwich", "Food sandwich", "food"),
        (49, "orange", "Orange fruit", "food"),
        (56, "chair", "Sitting chair", "furniture"),
        (57, "couch", "Living room couch", "furniture"),
        (59, "bed", "Sleeping bed", "furniture"),
        (60, "dining table", "Dining room table", "furniture"),
        (62, "tv", "Television screen", "electronics"),
        (63, "laptop", "Laptop computer", "electronics"),
        (64, "mouse", "Computer mouse", "electronics"),
        (65, "remote", "TV remote control", "electronics"),
        (66, "keyboard", "Computer keyboard", "electronics"),
        (67, "cell phone", "Mobile phone", "electronics"),
        (73, "book", "Reading book", "education"),
        (76, "scissors", "Cutting scissors", "tools"),
        (84, "book", "Reading book", "education"),
        (85, "clock", "Time clock", "accessories"),
    ]
    
    # Insert custom objects
    cursor.executemany('''
        INSERT OR REPLACE INTO objects (class_id, name, description, category)
        VALUES (?, ?, ?, ?)
    ''', custom_objects)
    
    # Insert COCO objects
    cursor.executemany('''
        INSERT OR REPLACE INTO objects (class_id, name, description, category)
        VALUES (?, ?, ?, ?)
    ''', coco_objects)
    
    # Create index for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_class_id ON objects(class_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON objects(name)')
    
    conn.commit()
    
    # Verify database creation
    cursor.execute('SELECT COUNT(*) FROM objects WHERE class_id >= 1000')
    custom_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM objects WHERE class_id < 1000')
    coco_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM objects')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("✅ Database created successfully!")
    print(f"📊 Added {custom_count} custom objects")
    print(f"📊 Added {coco_count} COCO objects")
    print(f"📊 Total objects in database: {total_count}")
    print(f"💾 Database saved as: {db_path}")
    
    return db_path

def verify_database():
    """Verify the database contents"""
    try:
        conn = sqlite3.connect('eyeknow_objects.db')
        cursor = conn.cursor()
        
        print("\n🔍 Database Verification:")
        
        # Show custom objects
        cursor.execute('SELECT class_id, name FROM objects WHERE class_id >= 1000 ORDER BY class_id')
        custom_objects = cursor.fetchall()
        print("\n📱 Custom Objects:")
        for obj in custom_objects:
            print(f"   {obj[0]}: {obj[1]}")
        
        # Show some COCO objects
        cursor.execute('SELECT class_id, name FROM objects WHERE class_id < 1000 ORDER BY class_id LIMIT 10')
        coco_objects = cursor.fetchall()
        print("\n🤖 Sample COCO Objects:")
        for obj in coco_objects:
            print(f"   {obj[0]}: {obj[1]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def get_object_by_class_id(class_id):
    """Get object information by class ID"""
    try:
        conn = sqlite3.connect('eyeknow_objects.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, description FROM objects WHERE class_id = ?', (class_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {'name': result[0], 'description': result[1]}
        else:
            return None
            
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Setting up EyeKnow Database...")
    print("=" * 50)
    
    # Create database
    db_path = create_database()
    
    # Verify creation
    if verify_database():
        print("\n✅ Database setup completed successfully!")
        print(f"📁 Database location: {os.path.abspath(db_path)}")
        print("\n🎯 Ready to run EyeKnow system!")
    else:
        print("\n❌ Database setup failed!")
    
    print("=" * 50)
